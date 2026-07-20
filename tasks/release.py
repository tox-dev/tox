"""Handles creating a release PR."""

from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError, check_call, run

from git import Commit, Head, Remote, Repo, TagReference
from packaging.version import Version

ROOT_SRC_DIR = Path(__file__).parents[1]


def cleanup_failed_release(  # ruff:ignore[too-many-arguments]
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
    print("Release failed! Cleaning up...")  # ruff:ignore[print]
    if release_created:
        print(f"Deleting GitHub release {version}")  # ruff:ignore[print]
        try:
            check_call(["gh", "release", "delete", str(version), "--yes"], cwd=str(ROOT_SRC_DIR))  # ruff:ignore[start-process-with-partial-path]
        except Exception as cleanup_error:  # ruff:ignore[blind-except]
            print(f"Warning: Failed to delete GitHub release: {cleanup_error}")  # ruff:ignore[print]
    if tag_pushed:
        print(f"Deleting remote tag {version}")  # ruff:ignore[print]
        try:
            repo.git.push(upstream.name, f":refs/tags/{version}", "--no-verify")
        except Exception as cleanup_error:  # ruff:ignore[blind-except]
            print(f"Warning: Failed to delete remote tag: {cleanup_error}")  # ruff:ignore[print]
    if main_pushed:
        print(f"Reverting main to {original_main_sha[:8]}")  # ruff:ignore[print]
        try:
            repo.git.push(upstream.name, f"{original_main_sha}:main", "-f", "--no-verify")
        except Exception as cleanup_error:  # ruff:ignore[blind-except]
            print(f"Warning: Failed to revert main: {cleanup_error}")  # ruff:ignore[print]
    print("Deleting remote release branch")  # ruff:ignore[print]
    try:
        repo.git.push(upstream.name, f":{release_branch}", "--no-verify")
    except Exception as cleanup_error:  # ruff:ignore[blind-except]
        print(f"Warning: Failed to delete remote branch: {cleanup_error}")  # ruff:ignore[print]


def main(version_str: str) -> None:
    version = Version(version_str)
    repo = Repo(str(ROOT_SRC_DIR))

    if repo.is_dirty():
        msg = "Current repository is dirty. Please commit any changes and try again."
        raise RuntimeError(msg)
    upstream, release_branch = create_release_branch(repo, version)
    original_main_sha = upstream.refs.main.commit.hexsha
    main_pushed, tag_pushed, release_created = False, False, False
    try:
        main_pushed, tag_pushed, release_created = _perform_release(repo, upstream, release_branch, version)
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


def _perform_release(repo: Repo, upstream: Remote, release_branch: Head, version: Version) -> tuple[bool, bool, bool]:
    release_commit = release_changelog(repo, version)
    tag = tag_release_commit(release_commit, repo, version)
    print("push release commit")  # ruff:ignore[print]
    repo.git.push(upstream.name, f"{release_branch}:main", "-f")
    main_pushed = True
    print("push release tag")  # ruff:ignore[print]
    repo.git.push(upstream.name, tag, "-f")
    tag_pushed = True
    create_github_release(version)
    release_created = True
    print("checkout main to new release and delete release branch")  # ruff:ignore[print]
    repo.heads.main.checkout()
    repo.delete_head(release_branch, force=True)
    print("delete remote release branch")  # ruff:ignore[print]
    repo.git.push(upstream.name, f":{release_branch}", "--no-verify")
    upstream.fetch()
    repo.git.reset("--hard", f"{upstream.name}/main")
    print("All done! ✨ 🍰 ✨")  # ruff:ignore[print]
    return main_pushed, tag_pushed, release_created


def create_release_branch(repo: Repo, version: Version) -> tuple[Remote, Head]:
    print("create release branch from upstream main")  # ruff:ignore[print]
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
    print("generate release commit")  # ruff:ignore[print]
    check_call(["towncrier", "build", "--yes", "--version", version.public], cwd=str(ROOT_SRC_DIR))  # ruff:ignore[start-process-with-partial-path]
    print("format changelog with pre-commit")  # ruff:ignore[print]
    changelog_path = ROOT_SRC_DIR / "docs" / "changelog.rst"
    try:
        check_call(["pre-commit", "run", "--files", str(changelog_path)], cwd=str(ROOT_SRC_DIR))  # ruff:ignore[start-process-with-partial-path]
    except CalledProcessError:
        print("pre-commit made formatting changes, staging them")  # ruff:ignore[print]
    repo.index.add([str(changelog_path)])
    return repo.index.commit(f"release {version}")


def tag_release_commit(release_commit: Commit, repo: Repo, version: Version) -> TagReference:
    print("tag release commit")  # ruff:ignore[print]
    existing_tags = [x.name for x in repo.tags]
    if version in existing_tags:
        print(f"delete existing tag {version}")  # ruff:ignore[print]
        repo.delete_tag(version)  # ty: ignore[invalid-argument-type] # Version has __str__, gitpython uses it
    print(f"create tag {version}")  # ruff:ignore[print]
    return repo.create_tag(version, ref=release_commit, force=True)  # ty: ignore[invalid-argument-type] # Version has __str__, gitpython uses it


def create_github_release(version: Version) -> None:
    print("create github release")  # ruff:ignore[print]
    version_str = str(version)
    try:
        result = run(
            ["gh", "release", "create", version_str, "--title", f"v{version_str}", "--generate-notes"],  # ruff:ignore[start-process-with-partial-path]
            cwd=str(ROOT_SRC_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout:
            print(result.stdout)  # ruff:ignore[print]
    except CalledProcessError as e:
        print(f"gh release create failed with exit code {e.returncode}")  # ruff:ignore[print]
        if e.stdout:
            print(f"stdout: {e.stdout}")  # ruff:ignore[print]
        if e.stderr:
            print(f"stderr: {e.stderr}")  # ruff:ignore[print]
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="release")
    parser.add_argument("--version", required=True)
    options = parser.parse_args()
    main(options.version)
