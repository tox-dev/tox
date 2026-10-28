# Security policy

tox is a command-line tool that creates isolated Python environments and runs the commands a project's configuration
names in them. This policy says how to report a security problem and how we decide whether a report is one.

## Reporting a vulnerability

**Do not open a public issue for a security problem.** Use
[GitHub's private vulnerability reporting](https://github.com/tox-dev/tox/security/advisories/new). If you do not have a
GitHub account, or you are a Tidelift subscriber, report through the
[Tidelift security contact](https://tidelift.com/security) instead; Tidelift coordinates the fix and the disclosure with
us. If neither works for you, email [gaborjbernat@gmail.com](mailto:gaborjbernat@gmail.com).

Include what the attacker controls and what they gain, the steps or a proof of concept, and the versions and platform
you tested. Write the report yourself; unreviewed tool or model output takes longer to triage.

## What to expect

Volunteers maintain tox, with no on-call rotation. We aim to acknowledge a report within **5 working days** and assess
it within **15 working days**. Fixes are developed in a private fork attached to the draft advisory, ship in a new
release, and the advisory, with a CVE requested through GitHub, goes out with that release. The default embargo is **90
days** from the report; we agree any change with the reporter. We credit reporters in the advisory under the name they
choose, or not at all. There is no bug bounty.

## Supported versions

Only the latest release receives fixes. Confirm the problem reproduces on it before reporting.

## Vulnerability or bug

A report is a vulnerability when an attacker who controls only an input that the [threat model](THREAT_MODEL.md) lists
as untrusted breaks a guarantee tox makes. A report that first needs control of something the threat model trusts, such
as the project's tox configuration, `toxfile.py`, or an installed tox plugin, is a bug: we fix it in the open and
publish no advisory. Classify by who supplies the dangerous input, not by how bad the outcome sounds.

**In scope**

- A secret-looking flag value that tox's redaction should mask appearing unmasked in tox's own log output.
- tox writing or deleting outside the work directory and paths the configuration names, for example while recreating an
  environment.
- Running a command, installing a package or loading a plugin that neither the configuration, the command line nor an
  installed plugin asked for.

**Out of scope**

- Commands, dependencies and `toxfile.py` code that the project's configuration specifies: running them is tox's
  purpose, so a malicious project is out of scope, as it is for every task runner.
- Code under test reading variables or files: `pass_env` keeps environments reproducible, it is not a sandbox against
  code running as the same user.
- Package installation behavior, which belongs to pip, uv or the installer plugin.
- Secrets printed by the commands tox runs.

If you cannot tell which side a finding falls on, report it privately and we will decide.
