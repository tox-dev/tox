from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from tox.util.file_view import create_session_view, repair_staging_path

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from tox.pytest import LogCaptureFixture, MonkeyPatch


@pytest.fixture
def package(tmp_path: Path) -> Path:
    path: Final[Path] = tmp_path / "pkg.whl"
    path.write_bytes(b"data")
    return path


def test_create_session_view_copies(tmp_path: Path, package: Path) -> None:
    result: Final[Path] = create_session_view(package, tmp_path / "temp", tmp_path)
    assert result.read_bytes() == b"data"
    assert result.parent.parent == tmp_path / "temp"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
@pytest.mark.parametrize(
    "umask",
    [pytest.param(0o002, id="group"), pytest.param(0o000, id="all"), pytest.param(0o022, id="owner")],
)
def test_create_session_view_private_directories(tmp_path: Path, package: Path, umask: int) -> None:
    staging: Final[Path] = tmp_path / ".tox" / ".tmp" / "package"
    previous: Final[int] = os.umask(umask)
    try:
        result: Final[Path] = create_session_view(package, staging, tmp_path)
    finally:
        os.umask(previous)

    assert result.read_bytes() == b"data"
    directories: Final[tuple[Path, ...]] = (staging.parent.parent, staging.parent, staging, result.parent)
    assert [stat.S_IMODE(directory.stat().st_mode) for directory in directories] == [0o700] * 4


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
@pytest.mark.parametrize("mode", [pytest.param(0o775, id="group"), pytest.param(0o2775, id="setgid")])
def test_create_session_view_accepts_group_writable_staging(tmp_path: Path, package: Path, mode: int) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    previous: Final[int] = os.umask(0o002)
    try:
        staging.mkdir(parents=True)
    finally:
        os.umask(previous)
    for directory in (work_dir, staging.parent, staging):
        directory.chmod(mode)
    tmp_path.chmod(0o775)

    result: Final[Path] = create_session_view(package, staging, tmp_path)

    assert result.read_bytes() == b"data"
    assert [stat.S_IMODE(path.stat().st_mode) for path in (tmp_path, work_dir, staging.parent, staging)] == [
        0o775,
        mode,
        mode,
        mode,
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_accepts_group_writable_work_dir_at_project_root(tmp_path: Path, package: Path) -> None:
    staging: Final[Path] = tmp_path / ".tmp" / "package"
    staging.mkdir(parents=True)
    tmp_path.chmod(0o775)
    for directory in (staging.parent, staging):
        directory.chmod(0o775)

    result: Final[Path] = create_session_view(package, staging, tmp_path)

    assert result.read_bytes() == b"data"
    assert [stat.S_IMODE(path.stat().st_mode) for path in (tmp_path, staging.parent, staging)] == [0o775, 0o775, 0o775]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_rejects_group_writable_staging_in_closed_project(tmp_path: Path, package: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o775)
    tmp_path.chmod(0o755)

    with pytest.raises(PermissionError, match="package staging path"):
        create_session_view(package, staging, tmp_path)

    assert stat.S_IMODE(work_dir.stat().st_mode) == 0o775


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_accepts_world_writable_staging_in_open_project(tmp_path: Path, package: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    tmp_path.chmod(0o777)
    for directory in (work_dir, staging.parent, staging):
        directory.chmod(0o777)

    result: Final[Path] = create_session_view(package, staging, tmp_path)

    assert result.read_bytes() == b"data"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory ownership")
def test_create_session_view_accepts_project_owner_staging_as_other_account(
    tmp_path: Path, package: Path, mocker: MockerFixture
) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    for directory in (work_dir, staging.parent, staging):
        directory.chmod(0o755)
    mocker.patch("os.geteuid", autospec=True, return_value=work_dir.stat().st_uid + 1)

    result: Final[Path] = create_session_view(package, staging, tmp_path)

    assert result.read_bytes() == b"data"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_error_names_owner_and_mode(tmp_path: Path, package: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o777)

    with pytest.raises(PermissionError) as error:
        create_session_view(package, staging, tmp_path)

    assert str(error.value) == (
        f"package staging path {work_dir} (owner uid {work_dir.stat().st_uid}, mode 0777) "
        f"can be changed by an account that cannot change {tmp_path}"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_locks_and_empties_legacy_work_dir(tmp_path: Path, caplog: LogCaptureFixture) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    planted: Final[Path] = work_dir / ".pkg" / "planted"
    planted.parent.mkdir(parents=True)
    planted.write_bytes(b"planted")
    work_dir.chmod(0o777)
    tmp_path.chmod(0o755)

    repair_staging_path(work_dir / ".tmp" / "package", tmp_path, work_dir)

    assert (stat.S_IMODE(work_dir.stat().st_mode), list(work_dir.iterdir())) == (0o700, [])
    assert f"{work_dir} could be changed by accounts that cannot change {tmp_path}" in caplog.text


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_locks_exposed_staging_only(tmp_path: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    for directory in (work_dir, staging.parent):
        directory.chmod(0o755)
    staging.chmod(0o777)
    (staging / "old").write_bytes(b"old")
    planted: Final[Path] = work_dir / ".pkg" / "planted"
    planted.parent.mkdir()
    planted.write_bytes(b"planted")
    tmp_path.chmod(0o755)

    repair_staging_path(staging, tmp_path, work_dir)

    assert (stat.S_IMODE(staging.stat().st_mode), list(staging.iterdir()), planted.exists()) == (0o755, [], True)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_keeps_private_directories(tmp_path: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    for directory in (work_dir, staging.parent):
        directory.chmod(0o700)
    staging.chmod(0o755)
    planted: Final[Path] = work_dir / ".pkg" / "planted"
    planted.parent.mkdir()
    planted.write_bytes(b"planted")
    tmp_path.chmod(0o755)

    repair_staging_path(staging, tmp_path, work_dir)

    assert (
        stat.S_IMODE(work_dir.stat().st_mode),
        stat.S_IMODE(staging.stat().st_mode),
        planted.exists(),
    ) == (0o700, 0o755, True)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_locks_work_dir_without_staging(tmp_path: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    work_dir.mkdir()
    (work_dir / "planted").write_bytes(b"planted")
    work_dir.chmod(0o777)
    tmp_path.chmod(0o755)

    repair_staging_path(work_dir / ".tmp" / "package", tmp_path, work_dir)

    assert (stat.S_IMODE(work_dir.stat().st_mode), list(work_dir.iterdir()), (work_dir / ".tmp").exists()) == (
        0o700,
        [],
        False,
    )


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_rejects_entry_owned_by_other_account(tmp_path: Path, mocker: MockerFixture) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    planted: Final[Path] = work_dir / ".pkg" / "planted"
    planted.parent.mkdir(parents=True)
    planted.write_bytes(b"planted")
    work_dir.chmod(0o777)
    tmp_path.chmod(0o755)
    original_lstat: Final[Callable[..., os.stat_result]] = os.lstat

    def lstat_as_other_account(path: Path, *, dir_fd: int | None = None) -> os.stat_result:
        values: Final[list[int | float]] = list(original_lstat(path, dir_fd=dir_fd))
        values[4] += int(path == planted)
        return os.stat_result(values)

    mocker.patch("os.lstat", autospec=True, side_effect=lstat_as_other_account)

    with pytest.raises(PermissionError, match="is owned by uid"):
        repair_staging_path(work_dir / ".tmp" / "package", tmp_path, work_dir)

    assert planted.read_bytes() == b"planted"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_keeps_running_environment(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    environment: Final[Path] = work_dir / "env"
    (environment / "bin").mkdir(parents=True)
    (environment / ".tox-info.json").write_text("{}")
    (work_dir / "junk").write_bytes(b"junk")
    work_dir.chmod(0o777)
    tmp_path.chmod(0o755)
    monkeypatch.setattr(sys, "prefix", str(environment))

    repair_staging_path(work_dir / ".tmp" / "package", tmp_path, work_dir)

    assert (
        sorted(path.name for path in work_dir.iterdir()),
        (environment / "bin").is_dir(),
        json.loads((environment / ".tox-info.json").read_text()),
    ) == (["env"], True, {"Python": {}})


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_leaves_exposed_intermediate_directory(tmp_path: Path, package: Path) -> None:
    build: Final[Path] = tmp_path / "build"
    work_dir: Final[Path] = build / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    tmp_path.chmod(0o755)
    build.chmod(0o775)

    repair_staging_path(staging, tmp_path, work_dir)

    assert stat.S_IMODE(build.stat().st_mode) == 0o775
    with pytest.raises(PermissionError, match="package staging path"):
        create_session_view(package, staging, tmp_path)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
@pytest.mark.parametrize(
    "owned",
    [pytest.param("build", id="intermediate"), pytest.param("build/.tox", id="work-dir")],
)
def test_repair_staging_path_skips_directory_owned_by_other_account(
    tmp_path: Path, mocker: MockerFixture, owned: str
) -> None:
    build: Final[Path] = tmp_path / "build"
    work_dir: Final[Path] = build / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o777)
    tmp_path.chmod(0o755)
    foreign_inode: Final[int] = (tmp_path / owned).stat().st_ino
    original_fstat: Final[Callable[[int], os.stat_result]] = os.fstat

    def fstat_as_other_account(descriptor: int) -> os.stat_result:
        values: Final[list[int | float]] = list(original_fstat(descriptor))
        values[4] += int(original_fstat(descriptor).st_ino == foreign_inode)
        return os.stat_result(values)

    mocker.patch("os.fstat", autospec=True, side_effect=fstat_as_other_account)

    repair_staging_path(staging, tmp_path, work_dir)

    assert stat.S_IMODE(work_dir.stat().st_mode) == 0o777


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
@pytest.mark.parametrize(
    ("replace", "linked"),
    [
        pytest.param(lambda moved, outside: moved.symlink_to(outside, target_is_directory=True), True, id="link"),
        pytest.param(lambda _moved, _outside: None, False, id="missing"),
    ],
)
def test_repair_staging_path_rejects_staging_child_swapped_during_repair(
    tmp_path: Path, mocker: MockerFixture, replace: Callable[[Path, Path], None], linked: bool
) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o775)
    outside: Final[Path] = tmp_path / "outside"
    (outside / "package").mkdir(parents=True)
    original_fchmod: Final[Callable[[int, int], None]] = os.fchmod
    work_inode: Final[int] = work_dir.stat().st_ino

    def swap_before_chmod(descriptor: int, mode: int) -> None:
        if os.fstat(descriptor).st_ino == work_inode:
            staging.parent.rename(tmp_path / "moved")
            replace(staging.parent, outside)
        original_fchmod(descriptor, mode)

    mocker.patch("os.fchmod", autospec=True, side_effect=swap_before_chmod)

    with pytest.raises(PermissionError, match="package staging path"):
        repair_staging_path(staging, tmp_path, work_dir)

    assert (staging.parent.is_symlink(), list((outside / "package").iterdir())) == (linked, [])


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_does_not_repair_outside_work_dir(tmp_path: Path, package: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    work_dir.mkdir()
    staging: Final[Path] = tmp_path / "outside" / "package"
    staging.mkdir(parents=True)
    staging.parent.chmod(0o775)

    repair_staging_path(staging, tmp_path, work_dir)
    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path)

    assert stat.S_IMODE(staging.parent.stat().st_mode) == 0o775


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
@pytest.mark.parametrize(
    "flag", [pytest.param("O_DIRECTORY", id="directory"), pytest.param("O_NOFOLLOW", id="nofollow")]
)
def test_repair_staging_path_skips_without_safe_open_flags(
    tmp_path: Path, package: Path, monkeypatch: MonkeyPatch, flag: str
) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o775)
    tmp_path.chmod(0o755)
    monkeypatch.delattr(os, flag, raising=False)

    repair_staging_path(staging, tmp_path, work_dir)

    assert stat.S_IMODE(work_dir.stat().st_mode) == 0o775
    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_repairs_nested_work_dir(tmp_path: Path, package: Path) -> None:
    shared: Final[Path] = tmp_path / "shared"
    work_dir: Final[Path] = shared / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    shared.chmod(0o755)
    work_dir.chmod(0o775)

    repair_staging_path(staging, tmp_path, work_dir)
    result: Final[Path] = create_session_view(package, staging, tmp_path)

    assert result.read_bytes() == b"data"
    assert stat.S_IMODE(shared.stat().st_mode) == 0o755
    assert stat.S_IMODE(work_dir.stat().st_mode) == 0o700


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_repair_staging_path_keeps_link_target_permissions(tmp_path: Path, package: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    work_dir.mkdir()
    outside: Final[Path] = tmp_path / "outside"
    (outside / "package").mkdir(parents=True)
    outside.chmod(0o775)
    (work_dir / ".tmp").symlink_to(outside, target_is_directory=True)

    repair_staging_path(work_dir / ".tmp" / "package", tmp_path, work_dir)
    with pytest.raises(PermissionError):
        create_session_view(package, work_dir / ".tmp" / "package", tmp_path)

    assert stat.S_IMODE(outside.stat().st_mode) == 0o775


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_does_not_repair_unmanaged_ancestor(tmp_path: Path, package: Path) -> None:
    shared: Final[Path] = tmp_path / "shared"
    work_dir: Final[Path] = shared / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    shared.chmod(0o775)
    work_dir.chmod(0o775)

    repair_staging_path(staging, tmp_path, work_dir)
    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path)

    assert (stat.S_IMODE(shared.stat().st_mode), stat.S_IMODE(work_dir.stat().st_mode)) == (0o775, 0o775)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_does_not_repair_traversing_work_dir(tmp_path: Path, package: Path) -> None:
    (tmp_path / "shared").mkdir()
    work_dir: Final[Path] = tmp_path / "shared" / ".." / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o775)

    repair_staging_path(staging, tmp_path, work_dir)
    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path)

    assert stat.S_IMODE(work_dir.stat().st_mode) == 0o775


def test_create_session_view_no_common_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "pkg.whl").write_bytes(b"data")
    monkeypatch.chdir(tmp_path)

    result: Final[Path] = create_session_view(Path("dist/pkg.whl"), tmp_path / "temp", tmp_path)

    assert result.is_absolute()
    assert result.read_bytes() == b"data"


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_create_session_view_replaces_staging_link(tmp_path: Path, package: Path) -> None:
    outside: Final[Path] = tmp_path / "outside"
    outside.mkdir()
    staging: Final[Path] = tmp_path / "temp"
    staging.symlink_to(outside, target_is_directory=True)

    result: Final[Path] = create_session_view(package, staging, tmp_path)

    assert (result.read_bytes(), staging.is_symlink(), list(outside.iterdir())) == (b"data", False, [])


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_create_session_view_does_not_follow_destination_link(
    tmp_path: Path, package: Path, mocker: MockerFixture
) -> None:
    outside: Final[Path] = tmp_path / "outside"
    outside.write_bytes(b"keep")
    mkdir: Final[Callable[[Path, int, bool, bool], None]] = Path.mkdir

    def mkdir_with_link(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir(path, mode, parents, exist_ok)
        if path.name == "1":
            (path / package.name).symlink_to(outside)

    mocker.patch.object(Path, "mkdir", autospec=True, side_effect=mkdir_with_link)

    with pytest.raises(FileExistsError):
        create_session_view(package, tmp_path / "temp", tmp_path)

    assert outside.read_bytes() == b"keep"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_rejects_writable_staging_parent(tmp_path: Path, package: Path) -> None:
    parent: Final[Path] = tmp_path / "temp"
    parent.mkdir(mode=0o777)
    parent.chmod(0o777)
    staging: Final[Path] = parent / "package"
    staging.mkdir()

    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path)

    assert stat.S_IMODE(parent.stat().st_mode) == 0o777
    assert list(staging.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_accepts_sticky_staging(tmp_path: Path, package: Path) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o1777)
    tmp_path.chmod(0o755)

    result: Final[Path] = create_session_view(package, staging, tmp_path)

    assert result.read_bytes() == b"data"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory ownership")
def test_create_session_view_rejects_other_account_staging_parent(
    tmp_path: Path, package: Path, mocker: MockerFixture
) -> None:
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o775)
    mocker.patch("os.geteuid", autospec=True, return_value=work_dir.stat().st_uid + 1)

    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path)

    assert stat.S_IMODE(work_dir.stat().st_mode) == 0o775
    assert list(staging.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX sticky directory permissions")
def test_create_session_view_rejects_foreign_link_in_sticky_parent(
    tmp_path: Path, package: Path, mocker: MockerFixture
) -> None:
    sticky: Final[Path] = tmp_path / "sticky"
    sticky.mkdir()
    sticky.chmod(0o1777)
    target: Final[Path] = tmp_path / "target"
    target.mkdir()
    link: Final[Path] = sticky / "link"
    link.symlink_to(target, target_is_directory=True)
    original_lstat: Final[Callable[[Path], os.stat_result]] = Path.lstat

    def lstat_as_other_account(path: Path) -> os.stat_result:
        values: Final[list[int | float]] = list(original_lstat(path))
        values[4] += int(path == link)
        return os.stat_result(values)

    mocker.patch.object(Path, "lstat", autospec=True, side_effect=lstat_as_other_account)

    with pytest.raises(PermissionError):
        create_session_view(package, link / "package", tmp_path)

    assert list((target / "package").iterdir()) == []
