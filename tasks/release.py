"""Handles creating a release PR."""

from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError, check_call, run

from git import Commit, Head, Remote, Repo, TagReference
from packaging.version import Version

ROOT_SRC_DIR = Path(__file__).parents[1]


def main(version_str: str) -> None:
    version = Version(version_str)
    repo = Repo(str(ROOT_SRC_DIR))

    if repo.is_dirty():
        msg = "Current repository is dirty. Please commit any changes and try again."
        raise RuntimeError(msg)
    upstream, release_branch = create_release_branch(repo, version)
    _perform_release(repo, upstream, release_branch, version)


def _perform_release(repo: Repo, upstream: Remote, release_branch: Head, version: Version) -> None:
    release_commit = release_changelog(repo, version)
    tag = tag_release_commit(release_commit, repo, version)
    print("push release commit")  # ruff:ignore[print]
    repo.git.push(upstream.name, f"{release_branch}:main")
    print("push release tag")  # ruff:ignore[print]
    repo.git.push(upstream.name, tag)
    create_github_release(version)
    print("checkout main to new release and delete release branch")  # ruff:ignore[print]
    repo.heads.main.checkout()
    repo.delete_head(release_branch, force=True)
    upstream.fetch()
    repo.git.reset("--hard", f"{upstream.name}/main")
    print("All done! ✨ 🍰 ✨")  # ruff:ignore[print]


def create_release_branch(repo: Repo, version: Version) -> tuple[Remote, Head]:
    print("create release branch from upstream main")  # ruff:ignore[print]
    upstream = get_upstream(repo)
    upstream.fetch()
    branch_name = f"release-{version}"
    release_branch = repo.create_head(branch_name, upstream.refs.main)
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
        check_call(["pre-commit", "run", "--files", str(changelog_path)], cwd=str(ROOT_SRC_DIR))  # ruff:ignore[start-process-with-partial-path]
    repo.git.add("-A", "--", "docs/changelog", "docs/changelog.rst")
    return repo.index.commit(f"release {version}")


def tag_release_commit(release_commit: Commit, repo: Repo, version: Version) -> TagReference:
    print("tag release commit")  # ruff:ignore[print]
    tag = str(version)
    if tag in {found.name for found in repo.tags}:
        msg = f"tag {tag} already exists"
        raise RuntimeError(msg)
    print(f"create tag {tag}")  # ruff:ignore[print]
    return repo.create_tag(tag, ref=release_commit.hexsha)


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
