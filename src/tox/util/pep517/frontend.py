"""Build frontend for PEP-517"""
import json
import shutil
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from time import sleep
from typing import Any, Dict, Iterator, List, NamedTuple, NoReturn, Optional, Set, Tuple, Type, cast
from zipfile import ZipFile

import toml
from packaging.requirements import Requirement

_HERE = Path(__file__).parent
ConfigSettings = Optional[Dict[str, Any]]


class CmdStatus(ABC):
    @property
    @abstractmethod
    def done(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def out_err(self) -> Tuple[str, str]:
        raise NotImplementedError


class WheelResult(NamedTuple):
    wheel: Path
    out: str
    err: str


class SdistResult(NamedTuple):
    sdist: Path
    out: str
    err: str


class MetadataForBuildWheelResult(NamedTuple):
    metadata: Path
    out: str
    err: str


class RequiresBuildWheelResult(NamedTuple):
    requires: Tuple[Requirement, ...]
    out: str
    err: str


class RequiresBuildSdistResult(NamedTuple):
    requires: Tuple[Requirement, ...]
    out: str
    err: str


class BackendFailed(RuntimeError):
    def __init__(self, result: Dict[str, Any], out: str, err: str) -> None:
        super().__init__()
        self.out = out
        self.err = err
        self.code: int = result["code"]
        self.exc_type: Type[Exception] = result["exc_type"]
        self.exc_msg: str = result["exc_msg"]

    def __str__(self) -> str:
        msg = [f"Backend failed with exit code {self.code}, exception type {self.exc_type} and message {self.exc_msg}"]
        if self.err.strip():
            msg.append(self.err)
        if self.out.strip():
            msg.append(self.out)
        return "\n".join(msg)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"result=dict(code={self.code}, exc_type={self.exc_type!r},exc_msg={self.exc_msg!r}),"
            f" out={self.out!r}, err={self.err!r})"
        )


class Frontend(ABC):
    LEGACY_BUILD_BACKEND: str = "setuptools.build_meta:__legacy__"
    LEGACY_REQUIRES: Tuple[Requirement, ...] = (Requirement("setuptools >= 40.8.0"), Requirement("wheel"))
    ALWAYS_EXIST = (
        "_commands",
        "_exit",
        "build_wheel",
        "build_sdist",
    )

    def __init__(
        self,
        root: Path,
        backend_paths: Tuple[Path, ...],
        backend_module: str,
        backend_obj: Optional[str],
        requires: Tuple[Requirement, ...],
    ) -> None:
        self._root = root
        self._backend_paths = backend_paths
        self._backend_module = backend_module
        self._backend_obj = backend_obj
        self._requires = requires
        self._commands: Optional[Set[str]] = None

    @classmethod
    def create_args_from_folder(
        cls, folder: Path
    ) -> Tuple[Path, Tuple[Path, ...], str, Optional[str], Tuple[Requirement, ...]]:
        py_project_toml = folder / "pyproject.toml"
        if py_project_toml.exists():
            py_project = toml.load(py_project_toml)
            build_system = py_project.get("build-system", {})
            if "backend-path" in build_system:
                backend_paths: Tuple[Path, ...] = tuple(folder / p for p in build_system["backend-path"])
            else:
                backend_paths = ()
            if "requires" in build_system:
                requires: Tuple[Requirement, ...] = tuple(Requirement(r) for r in build_system.get("requires"))
            else:
                requires = cls.LEGACY_REQUIRES
            build_backend = build_system.get("build-backend", cls.LEGACY_BUILD_BACKEND)
        else:
            backend_paths = ()
            requires = cls.LEGACY_REQUIRES
            build_backend = cls.LEGACY_BUILD_BACKEND
        paths = build_backend.split(":")
        backend_module: str = paths[0]
        backend_obj: Optional[str] = paths[1] if len(paths) > 1 else None
        return folder, backend_paths, backend_module, backend_obj, requires

    def build_sdist(self, sdist_directory: Path, config_settings: Optional[ConfigSettings] = None) -> SdistResult:
        sdist_directory.mkdir(parents=True, exist_ok=True)
        basename, out, err = self._send(
            cmd="build_sdist",
            sdist_directory=sdist_directory,
            config_settings=config_settings,
            missing=None,
        )
        if basename is None:
            self._required_command_missing("build_sdist")
        return SdistResult(sdist_directory / basename, out, err)

    def build_wheel(
        self,
        wheel_directory: Path,
        config_settings: Optional[ConfigSettings] = None,
        metadata_directory: Optional[Path] = None,
    ) -> WheelResult:
        wheel_directory.mkdir(parents=True, exist_ok=True)
        basename, out, err = self._send(
            cmd="build_wheel",
            wheel_directory=wheel_directory,
            config_settings=config_settings,
            metadata_directory=metadata_directory,
            missing=None,
        )
        if basename is None:
            self._required_command_missing("build_wheel")
        return WheelResult(wheel_directory / basename, out, err)

    def _required_command_missing(self, cmd: str) -> NoReturn:
        msg = f"{cmd} cannot be missing on backend {self.backend!r}"
        raise BackendFailed({"code": None, "exc_type": ValueError.__name__, "exc_msg": msg}, "", "")

    @property
    def backend(self) -> str:
        return f"{self._backend_module}{f':{self._backend_obj}' if self._backend_obj else ''}"

    def prepare_metadata_for_build_wheel(
        self, metadata_directory: Path, config_settings: Optional[ConfigSettings] = None
    ) -> MetadataForBuildWheelResult:
        if metadata_directory.exists():  #
            shutil.rmtree(metadata_directory)
        metadata_directory.mkdir(parents=True, exist_ok=True)
        basename, out, err = self._send(
            cmd="prepare_metadata_for_build_wheel",
            metadata_directory=metadata_directory,
            config_settings=config_settings,
            missing=None,
        )
        if basename is None:  # if backend does not provide it acquire it from the wheel
            basename, err, out = self._metadata_from_built_wheel(config_settings, metadata_directory)
        result = metadata_directory / basename
        return MetadataForBuildWheelResult(result, out, err)

    def _metadata_from_built_wheel(
        self, config_settings: Optional[ConfigSettings], metadata_directory: Optional[Path]
    ) -> Tuple[str, str, str]:
        with self._wheel_directory() as wheel_directory:
            wheel_result = self.build_wheel(
                wheel_directory=wheel_directory,
                config_settings=config_settings,
                metadata_directory=metadata_directory,
            )
            wheel = wheel_result.wheel
            out, err = wheel_result.out, wheel_result.err
            extract_to = str(metadata_directory)
            with ZipFile(str(wheel), "r") as zip_file:
                for name in zip_file.namelist():
                    path = Path(name)
                    if path.parts[0].endswith(".dist-info"):
                        basename = path.parts[0]
                        zip_file.extract(name, extract_to)
            if basename is None:
                raise RuntimeError(f"no .dist-info found inside generated wheel {wheel}")
        return basename, err, out

    @contextmanager
    def _wheel_directory(self) -> Iterator[Path]:
        with TemporaryDirectory() as wheel_directory:
            yield Path(wheel_directory)

    def get_requires_for_build_wheel(
        self, config_settings: Optional[ConfigSettings] = None
    ) -> RequiresBuildWheelResult:
        result, out, err = self._send(cmd="get_requires_for_build_wheel", config_settings=config_settings, missing=[])
        return RequiresBuildWheelResult(tuple(Requirement(r) for r in cast(List[str], result)), out, err)

    def get_requires_for_build_sdist(
        self, config_settings: Optional[ConfigSettings] = None
    ) -> RequiresBuildSdistResult:
        result, out, err = self._send(cmd="get_requires_for_build_sdist", config_settings=config_settings, missing=[])
        return RequiresBuildSdistResult(tuple(Requirement(r) for r in cast(List[str], result)), out, err)

    @property
    def commands(self) -> Set[str]:
        if self._commands is None:
            raw, _, __ = self._send("_commands", missing=[])
            self._commands = set(raw)
        return self._commands

    def _send(self, cmd: str, missing: Any, **kwargs: Any) -> Tuple[Any, str, str]:
        if cmd not in self.ALWAYS_EXIST and cmd not in self.commands:
            return missing, "", ""
        with NamedTemporaryFile(prefix=f"pep517_{cmd}-") as result_file_marker:
            result_file = Path(result_file_marker.name).with_suffix(".json")
            msg = json.dumps(
                {
                    "cmd": cmd,
                    "kwargs": {k: (str(v) if isinstance(v, Path) else v) for k, v in kwargs.items()},
                    "result": str(result_file),
                }
            )
            with self._send_msg(cmd, result_file, msg) as status:
                while not status.done:
                    sleep(0.001)  # wait a bit for things to happen
            if result_file.exists():
                try:
                    with result_file.open("rt") as result_handler:
                        result = json.load(result_handler)
                finally:
                    result_file.unlink()
            else:
                result = {
                    "code": 1,
                    "exc_type": "RuntimeError",
                    "exc_msg": f"Backend response file {result_file} is missing",
                }
            out, err = status.out_err()
            if "return" in result:
                return result["return"], out, err
            raise BackendFailed(result, out, err)

    @property
    def backend_args(self) -> List[str]:
        result: List[str] = [str(_HERE / "backend.py"), self._backend_module]
        if self._backend_obj:
            result.append(self._backend_obj)
        return result

    @abstractmethod
    @contextmanager
    def _send_msg(self, cmd: str, result_file: Path, msg: str) -> Iterator[CmdStatus]:
        raise NotImplementedError
