# -*- coding: utf-8 -*-
"""Handles creating a release PR"""
import base64
import json
import os
import tempfile
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Tuple

import httplib2
from apiclient import discovery
from git import Remote, Repo
from oauth2client import client, file, tools
from packaging.version import Version

ROOT_SRC_DIR = Path(__file__).parents[1]


def main() -> None:
    repo = Repo(str(ROOT_SRC_DIR))
    update_upstream(repo)
    prev_version, release_version = get_last_release_versions(repo)
    send_mail_message(
        subject=f"tox release {release_version}",
        content=get_message_body(release_version, prev_version),
    )
    print("All done! ✨ 🍰 ✨")


def get_message_body(release_version: Version, prev_version: Version) -> str:
    is_major_release = release_version.release[0:2] != prev_version.release[0:2]
    if is_major_release:
        return textwrap.dedent(
            f"""
        The tox team is proud to announce the {release_version} feature release at https://pypi.org/project/tox/!

        tox aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging, testing and release process of Python software.

        Details about the changes can be found at https://tox.readthedocs.io/en/{release_version}/changelog.html
        For complete documentation, please visit: https://tox.readthedocs.io/en/{release_version}/

        As usual, you can upgrade from PyPI via:

            pip install --upgrade tox

        or - if you also want to get pre release versions:

            pip install -upgrade --pre tox

        We thank all present and past contributors to tox. Have a look at https://github.com/tox-dev/tox/blob/master/CONTRIBUTORS to see who contributed.

        Happy toxing,
        the tox-dev team
        """  # noqa
        )
    else:
        return textwrap.dedent(
            f"""
                The tox team is proud to announce the {release_version} bug fix release at https://pypi.org/project/tox/!

                tox aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging, testing and release process of Python software.

                For details about the fix(es),please check the CHANGELOG: https://tox.readthedocs.io/en/{release_version}/changelog.html

                We thank all present and past contributors to tox. Have a look at https://github.com/tox-dev/tox/blob/master/CONTRIBUTORS to see who contributed.

                Happy toxing,
                the tox-dev team
                """  # noqa
        )


def get_upstream(repo: Repo) -> Remote:
    for remote in repo.remotes:
        for url in remote.urls:
            if url.endswith("tox-dev/tox.git"):
                return remote
    raise RuntimeError("could not find tox-dev/tox.git remote")


def get_last_release_versions(repo: Repo) -> Tuple[Version, Version]:
    print("get latest release version")
    commit_to_tag = {tag.commit.hexsha: tag for tag in repo.tags}
    _, release_tag = sorted(
        [(tag.commit.committed_datetime, tag) for tag in repo.tags], reverse=True
    )[0]
    for commit in release_tag.commit.iter_parents():
        if commit.hexsha in commit_to_tag:
            prev_release_tag = commit_to_tag[commit.hexsha]
            prev_version = Version(prev_release_tag.name)
            if not any(
                (
                    prev_version.is_devrelease,
                    prev_version.is_prerelease,
                    prev_version.is_postrelease,
                )
            ):
                break
    else:
        raise RuntimeError("no previous release")
    release_version = Version(release_tag.name)
    print(f"\trelease {release_version} with previous {prev_version}")
    return prev_version, release_version


def update_upstream(repo: Repo) -> None:
    print("fetch latest remote")
    upstream = get_upstream(repo)
    upstream.fetch()


def send_mail_message(subject, content):
    this_dir = Path(__file__).parent
    store = file.Storage("credentials.json")
    credentials = store.get()
    if not credentials or credentials.invalid:
        client_secret_json = json.loads((this_dir / "client_secret.json").read_text())
        client_secret_json["installed"]["client_secret"] = os.environ["TOX_DEV_GOOGLE_SECRET"]
        with tempfile.NamedTemporaryFile(mode="w+t") as temp_filename:
            json.dump(client_secret_json, temp_filename)
            temp_filename.flush()
            flow = client.flow_from_clientsecrets(
                filename=temp_filename.name, scope="https://www.googleapis.com/auth/gmail.send"
            )
            credentials = tools.run_flow(flow, store)
    service = discovery.build("gmail", "v1", http=credentials.authorize(httplib2.Http()))

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = "toxdevorg@gmail.com"
    recipients = ["testing-in-python@lists.idyll.org", "tox-dev@python.org"]
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(content, "plain"))
    raw_message_no_attachment = base64.urlsafe_b64encode(message.as_bytes())
    raw_message_no_attachment = raw_message_no_attachment.decode()
    body = {"raw": raw_message_no_attachment}
    message_sent = service.users().messages().send(userId="me", body=body).execute()
    message_id = message_sent["id"]
    print(f"\tMessage sent with id: {message_id}")


if __name__ == "__main__":
    main()
