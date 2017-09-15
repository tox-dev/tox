# Towncrier news

If you contribute something non trivial to the tox project, let the world know of the fantastic improvements you brought. To that end all you have to do is add a file here filled with thrilling new about what you did.

To see what news sections there are see the type sections in [pyproject](../../pyproject.toml) - the naming follows the following scheme

    <issue id> | pr<pull request id>.type.rst

e.g.

    614.feature.rst
    pr324.bugfix.rst

The changes get rendered to [CHANGELOG](../../CHANGELOG.rst) and will be the most important source of news for our beloved users.

## Full example


```rst
This is the change to end all changes. I deleted all lines of code
containing the letter `p` might break some things, but works for me - 
by @obestwalter.
```

