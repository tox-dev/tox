"""Handles creating a release PR."""

from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError, check_call, run

from git import Commit, Head, Remote, Repo, TagReference
from packaging.version import Version

ROOT_SRC_DIR = Path(__file__).parents[1]


def cleanup_failed_release(  # noqa: PLR0913
    repo: Repo,
    upstream: Remote,
    version: Version,
    release_branch: Head,
    original_main_sha: str,
    *,
    release_created: bool,
    tag_pushed: bool,
    main_pushed: bool,
) -> None:
    print("Release failed! Cleaning up...")  # noqa: T201
    if release_created:
        print(f"Deleting GitHub release {version}")  # noqa: T201
        try:
            check_call(["gh", "release", "delete", str(version), "--yes"], cwd=str(ROOT_SRC_DIR))  # noqa: S607
        except Exception as cleanup_error:  # noqa: BLE001
            print(f"Warning: Failed to delete GitHub release: {cleanup_error}")  # noqa: T201
    if tag_pushed:
        print(f"Deleting remote tag {version}")  # noqa: T201
        try:
            repo.git.push(upstream.name, f":refs/tags/{version}", "--no-verify")
        except Exception as cleanup_error:  # noqa: BLE001
            print(f"Warning: Failed to delete remote tag: {cleanup_error}")  # noqa: T201
    if main_pushed:
        print(f"Reverting main to {original_main_sha[:8]}")  # noqa: T201
        try:
            repo.git.push(upstream.name, f"{original_main_sha}:main", "-f", "--no-verify")
        except Exception as cleanup_error:  # noqa: BLE001
            print(f"Warning: Failed to revert main: {cleanup_error}")  # noqa: T201
    print("Deleting remote release branch")  # noqa: T201
    try:
        repo.git.push(upstream.name, f":{release_branch}", "--no-verify")
    except Exception as cleanup_error:  # noqa: BLE001
        print(f"Warning: Failed to delete remote branch: {cleanup_error}")  # noqa: T201


def main(version_str: str) -> None:
    version = Version(version_str)
    repo = Repo(str(ROOT_SRC_DIR))

    if repo.is_dirty():
        msg = "Current repository is dirty. Please commit any changes and try again."
        raise RuntimeError(msg)
    upstream, release_branch = create_release_branch(repo, version)
    main_pushed = False
    tag_pushed = False
    release_created = False
    original_main_sha = upstream.refs.main.commit.hexsha
    try:
        release_commit = release_changelog(repo, version)
        tag = tag_release_commit(release_commit, repo, version)
        print("push release commit")  # noqa: T201
        repo.git.push(upstream.name, f"{release_branch}:main", "-f")
        main_pushed = True
        print("push release tag")  # noqa: T201
        repo.git.push(upstream.name, tag, "-f")
        tag_pushed = True
        create_github_release(version)
        release_created = True
        print("checkout main to new release and delete release branch")  # noqa: T201
        repo.heads.main.checkout()
        repo.delete_head(release_branch, force=True)
        print("delete remote release branch")  # noqa: T201
        repo.git.push(upstream.name, f":{release_branch}", "--no-verify")
        upstream.fetch()
        repo.git.reset("--hard", f"{upstream.name}/main")
        print("All done! ✨ 🍰 ✨")  # noqa: T201
    except Exception:
        cleanup_failed_release(
            repo,
            upstream,
            version,
            release_branch,
            original_main_sha,
            release_created=release_created,
            tag_pushed=tag_pushed,
            main_pushed=main_pushed,
        )
        raise


def create_release_branch(repo: Repo, version: Version) -> tuple[Remote, Head]:
    print("create release branch from upstream main")  # noqa: T201
    upstream = get_upstream(repo)
    upstream.fetch()
    branch_name = f"release-{version}"
    release_branch = repo.create_head(branch_name, upstream.refs.main, force=True)
    upstream.push(refspec=f"{branch_name}:{branch_name}", force=True)
    release_branch.set_tracking_branch(repo.refs[f"{upstream.name}/{branch_name}"])  # ty: ignore[invalid-argument-type] # gitpython types Reference broadly
    release_branch.checkout()
    return upstream, release_branch


def get_upstream(repo: Repo) -> Remote:
    for remote in repo.remotes:
        if any("tox-dev/tox" in url for url in remote.urls):
            return remote
    msg = "could not find tox-dev/tox remote"
    raise RuntimeError(msg)


def release_changelog(repo: Repo, version: Version) -> Commit:
    print("generate release commit")  # noqa: T201
    check_call(["towncrier", "build", "--yes", "--version", version.public], cwd=str(ROOT_SRC_DIR))  # noqa: S607
    print("format changelog with pre-commit")  # noqa: T201
    changelog_path = ROOT_SRC_DIR / "docs" / "changelog.rst"
    try:
        check_call(["pre-commit", "run", "--files", str(changelog_path)], cwd=str(ROOT_SRC_DIR))  # noqa: S607
    except CalledProcessError:
        print("pre-commit made formatting changes, staging them")  # noqa: T201
    repo.index.add([str(changelog_path)])
    return repo.index.commit(f"release {version}")


def tag_release_commit(release_commit: Commit, repo: Repo, version: Version) -> TagReference:
    print("tag release commit")  # noqa: T201
    existing_tags = [x.name for x in repo.tags]
    if version in existing_tags:
        print(f"delete existing tag {version}")  # noqa: T201
        repo.delete_tag(version)  # ty: ignore[invalid-argument-type] # Version has __str__, gitpython uses it
    print(f"create tag {version}")  # noqa: T201
    return repo.create_tag(version, ref=release_commit, force=True)  # ty: ignore[invalid-argument-type] # Version has __str__, gitpython uses it


def create_github_release(version: Version) -> None:
    print("create github release")  # noqa: T201
    version_str = str(version)
    try:
        result = run(
            ["gh", "release", "create", version_str, "--title", f"v{version_str}", "--generate-notes"],  # noqa: S607
            cwd=str(ROOT_SRC_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout:
            print(result.stdout)  # noqa: T201
    except CalledProcessError as e:
        print(f"gh release create failed with exit code {e.returncode}")  # noqa: T201
        if e.stdout:
            print(f"stdout: {e.stdout}")  # noqa: T201
        if e.stderr:
            print(f"stderr: {e.stderr}")  # noqa: T201
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="release")
    parser.add_argument("--version", required=True)
    options = parser.parse_args()
    main(options.version)
