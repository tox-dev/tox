"""Handles creating a release PR."""
from __future__ import annotations

from pathlib import Path
from subprocess import check_call

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
    try:
        release_commit = release_changelog(repo, version)
        tag = tag_release_commit(release_commit, repo, version)
        print("push release commit")  # noqa: T201
        repo.git.push(upstream.name, f"{release_branch}:main", "-f")
        print("push release tag")  # noqa: T201
        repo.git.push(upstream.name, tag, "-f")
    finally:
        print("checkout main to new release and delete release branch")  # noqa: T201
        repo.heads.main.checkout()
        repo.delete_head(release_branch, force=True)
        upstream.fetch()
        repo.git.reset("--hard", "upstream/main")
    print("All done! ✨ 🍰 ✨")  # noqa: T201


def create_release_branch(repo: Repo, version: Version) -> tuple[Remote, Head]:
    print("create release branch from upstream main")  # noqa: T201
    upstream = get_upstream(repo)
    upstream.fetch()
    branch_name = f"release-{version}"
    release_branch = repo.create_head(branch_name, upstream.refs.main, force=True)
    upstream.push(refspec=f"{branch_name}:{branch_name}", force=True)
    release_branch.set_tracking_branch(repo.refs[f"{upstream.name}/{branch_name}"])
    release_branch.checkout()
    return upstream, release_branch


def get_upstream(repo: Repo) -> Remote:
    for remote in repo.remotes:
        if any(url.endswith("tox-dev/tox.git") for url in remote.urls):
            return remote
    msg = "could not find tox-dev/tox.git remote"
    raise RuntimeError(msg)


def release_changelog(repo: Repo, version: Version) -> Commit:
    print("generate release commit")  # noqa: T201
    check_call(["towncrier", "build", "--yes", "--version", version.public], cwd=str(ROOT_SRC_DIR))  # noqa: S607, S603
    return repo.index.commit(f"release {version}")


def tag_release_commit(release_commit: Commit, repo: Repo, version: Version) -> TagReference:
    print("tag release commit")  # noqa: T201
    existing_tags = [x.name for x in repo.tags]
    if version in existing_tags:
        print(f"delete existing tag {version}")  # noqa: T201
        repo.delete_tag(version)
    print(f"create tag {version}")  # noqa: T201
    return repo.create_tag(version, ref=release_commit, force=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="release")
    parser.add_argument("--version", required=True)
    options = parser.parse_args()
    main(options.version)
