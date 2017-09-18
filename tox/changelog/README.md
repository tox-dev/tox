# Towncrier news

If you contribute something non trivial to the tox project, let the world know of the fantastic improvements you brought. To that end all you have to do is add a file here filled with thrilling new about what you did.

To see what news sections there are see the type sections in [pyproject](../../pyproject.toml) - the naming follows the following scheme

    <issue or pull request number>.type.rst

e.g.

    614.feature.rst
    324.bugfix.rst

The changes get rendered to [CHANGELOG](../../CHANGELOG.rst) and will be the most important source of news for our beloved users.

## Full example

file `tox/changelog/666.rst`:

```rst
This is the change to end all changes. I deleted all lines of code
containing the letter `p`!

Might break some things, but works for me.

by @obestwalter.
```
