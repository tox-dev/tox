"""This package handles provisioning an appropriate tox version per requirements."""

from __future__ import annotations

import json
import locale
import logging
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast
from urllib.parse import urlsplit

from filelock import FileLock
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from tox.config.loader.memory import MemoryLoader
from tox.execute.api import StdinSource
from tox.plugin import impl
from tox.report import HandledError
from tox.tox_env.errors import Skip
from tox.tox_env.python.pip.req_file import PythonDeps
from tox.util.redact import redact_argv

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from importlib.metadata import Distribution
    from urllib.parse import SplitResult

    from tox.session.state import State
    from tox.tox_env.python.runner import PythonRun
    from tox.util.json_types import JsonValue


# pip records only these URL fragment hashes in direct_url.json.
_PIP_HASH_ALGORITHMS: Final[frozenset[str]] = frozenset({
    "md5",
    "sha1",
    "sha224",
    "sha256",
    "sha384",
    "sha512",
})


@impl
def tox_add_option(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--no-provision",
        default=False,
        const=True,
        nargs="?",
        metavar="REQ_JSON",
        help="do not perform provision, but fail and if a path was provided write provision metadata as JSON to it",
    )
    parser.add_argument(
        "--no-recreate-provision",
        dest="no_recreate_provision",
        help="if recreate is set do not recreate provision tox environment",
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--recreate",
        dest="recreate",
        help="recreate the tox environments",
        action="store_true",
    )


def provision(state: State) -> int | bool:
    # remove the dev and marker to allow local development of the package
    state.conf.core.add_config(
        keys=["min_version", "minversion"],
        of_type=Version,
        # do not include local version specifier (because it's not allowed in version spec per PEP-440)
        default=None,  # Optional[Version] translates to object
        desc="Define the minimal tox version required to run",
    )
    state.conf.core.add_config(
        keys="provision_tox_env",
        of_type=str,
        default=".tox",
        desc="Name of the virtual environment used to provision a tox.",
    )

    def add_tox_requires_min_version(reqs: list[Requirement]) -> list[Requirement]:
        min_version = state.conf.core.get_optional("min_version", Version)
        reqs.append(Requirement(f"tox{f'>={min_version}' if min_version else ''}"))
        return reqs

    state.conf.core.add_config(
        keys="requires",
        of_type=list[Requirement],
        default=[],
        desc="Dependencies the Python environment hosting tox must satisfy, provisioned when missing",
        post_process=add_tox_requires_min_version,
    )

    from tox.plugin.manager import MANAGER  # ruff:ignore[import-outside-top-level]

    MANAGER.tox_add_core_config(state.conf.core, state)

    requires = state.conf.core.get("requires", list[Requirement])
    missing = _get_missing(requires)

    deps = ", ".join(f"{p}{'' if v is None else f' ({v})'}" for p, v in missing)
    loader = MemoryLoader(  # these configuration values are loaded from in-memory always (no file conf)
        base=[],  # disable inheritance for provision environments
        skip_install=True,  # no packaging, including artifacts selected with --installpkg
        # use our own dependency specification
        deps=PythonDeps(requires, root=state.conf.core["tox_root"]),
        pass_env=["*"],  # do not filter environment variables, will be handled by provisioned tox
        recreate=state.conf.options.recreate and not state.conf.options.no_recreate_provision,
    )
    provision_tox_env = state.conf.core.get("provision_tox_env", str)
    state.conf.memory_seed_loaders[provision_tox_env].append(loader)
    state.envs._mark_provision(bool(missing), provision_tox_env)  # ruff:ignore[private-member-access]

    if not missing:
        if remainder := state.conf.options.remainder:
            msg = (
                f"unrecognized arguments: {' '.join(redact_argv(remainder))}\n"
                "hint: if you tried to pass arguments to a command use -- to separate them from tox ones"
            )
            raise HandledError(msg)
        return False

    miss_msg = f"is missing [requires (has)]: {deps}"

    no_provision: bool | str = state.conf.options.no_provision
    if no_provision:
        msg = f"provisioning explicitly disabled within {sys.executable}, but {miss_msg}"
        if isinstance(no_provision, str):
            msg += f" and wrote to {no_provision}"
            tox_specifier = next(i.specifier for i in requires if i.name == "tox")
            requires_dict = {
                "minversion": next((s.version for s in tox_specifier if s.operator in {">=", "=="}), None),
                "requires": [str(i) for i in requires],
            }
            Path(no_provision).write_text(
                json.dumps(requires_dict, indent=4), encoding=locale.getpreferredencoding(do_setlocale=False)
            )
        raise HandledError(msg)

    logging.warning("will run in automatically provisioned tox, host %s %s", sys.executable, miss_msg)
    return run_provision(provision_tox_env, state)


def _get_missing(requires: list[Requirement]) -> list[tuple[Requirement, str | None]]:
    missing: list[tuple[Requirement, str | None]] = []
    for package in requires:
        if package.marker and not package.marker.evaluate():
            continue
        package_name = canonicalize_name(package.name)
        try:
            dist = distribution(package_name)
        except PackageNotFoundError:
            missing.append((package, None))
        else:
            if package.url is not None:
                if not _installed_from_url(dist, package.url):
                    missing.append((package, dist.version))
            elif not package.specifier.contains(dist.version, prereleases=True):
                missing.append((package, dist.version))
    return missing


def _installed_from_url(dist: Distribution, url: str) -> bool:
    try:
        info: Final[JsonValue] = json.loads(dist.read_text("direct_url.json") or "null")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(info, dict) or not isinstance(installed := info.get("url"), str):
        return False
    if not any(isinstance(info.get(kind), dict) for kind in ("vcs_info", "archive_info", "dir_info")):
        return False
    if isinstance(vcs_info := info.get("vcs_info"), dict) and isinstance(vcs := vcs_info.get("vcs"), str):
        installed = f"{vcs}+{installed}"
        if isinstance(revision := vcs_info.get("requested_revision"), str):
            installed = f"{installed}@{revision}"
    requested, _, fragment = url.partition("#")
    if installed != requested:
        try:
            parts: Final[SplitResult] = urlsplit(requested)
        except ValueError:
            return False
        if "@" not in parts.netloc or installed != parts._replace(netloc=parts.netloc.rsplit("@", 1)[1]).geturl():
            return False
        if not isinstance(info.get("archive_info"), dict) or not any(
            algorithm in _PIP_HASH_ALGORITHMS for algorithm, _ in _fragment_fields(fragment)
        ):
            msg = "cannot verify the installed origin of a credentialed direct URL without an archive hash"
            raise HandledError(msg)
    return _origin_fragment_matches(info, fragment)


def _fragment_fields(fragment: str) -> list[tuple[str, str]]:
    # pip retains percent escapes and plus signs in the recorded subdirectory.
    fields: Final[list[tuple[str, str]]] = []
    for part in fragment.split("&"):
        key, separator, value = part.partition("=")
        if separator:
            fields.append((key, value))
    return fields


def _origin_fragment_matches(info: dict[str, JsonValue], fragment: str) -> bool:
    fields: Final[list[tuple[str, str]]] = _fragment_fields(fragment)
    if (next((value for key, value in fields if key == "subdirectory"), None) or None) != info.get("subdirectory"):
        return False
    hash_fragment: Final[tuple[str, str] | None] = next(
        ((key, value) for key, value in fields if key in _PIP_HASH_ALGORITHMS), None
    )
    if hash_fragment is None:
        return True
    archive_info: Final[JsonValue] = info.get("archive_info")
    if not isinstance(archive_info, dict):
        return False
    algorithm, expected = hash_fragment
    hashes: Final[JsonValue] = archive_info.get("hashes")
    actual = hashes.get(algorithm) if isinstance(hashes, dict) else None
    if actual is None and isinstance(legacy_hash := archive_info.get("hash"), str):
        legacy_algorithm, _, legacy_value = legacy_hash.partition("=")
        if legacy_algorithm == algorithm:
            actual = legacy_value
    return isinstance(actual, str) and actual.lower() == expected.lower()


def run_provision(name: str, state: State) -> int:
    tox_env: PythonRun = cast("PythonRun", state.envs[name])
    env_python = tox_env.env_python()
    logging.info("will run in a automatically provisioned python environment under %s", env_python)
    lock_path = tox_env.env_dir / "file.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(lock_path):
        try:
            return _setup_and_execute(tox_env, env_python, state)
        except Skip as exception:
            msg = f"cannot provision tox environment {tox_env.conf['env_name']} because {exception}"
            raise HandledError(msg) from exception
        finally:
            tox_env.teardown()


def _setup_and_execute(tox_env: PythonRun, env_python: Path, state: State) -> int:
    tox_env.setup()
    # -m adds the start directory to sys.path, where another user may have planted a module.
    args: list[str] = [str(env_python), "-P" if tox_env.base_python.version_info >= (3, 11) else "-I", "-m", "tox"]
    if state.conf.options.is_colored and "--colored" not in state.args:
        args.extend(["--colored", "yes"])
    args.extend(state.args)
    outcome = tox_env.execute(cmd=args, stdin=StdinSource.user_only(), show=True, run_id="provision", cwd=Path.cwd())
    return cast("int", outcome.exit_code)


__all__ = [
    "provision",
]
