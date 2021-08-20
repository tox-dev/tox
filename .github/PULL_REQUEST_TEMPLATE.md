## Thanks for contributing a pull request!

If you are contributing for the first time or provide a trivial fix don't worry too
much about the checklist - we will help you get started.

## Contribution checklist:

(also see [CONTRIBUTING.rst](../tree/master/CONTRIBUTING.rst) for details)

- [ ] wrote descriptive pull request text
- [ ] added/updated test(s)
- [ ] updated/extended the documentation
- [ ] added relevant [issue keyword](https://help.github.com/articles/closing-issues-using-keywords/)
      in message body
- [ ] added news fragment in [changelog folder](../tree/master/docs/changelog)
  * fragment name: `<issue number>.<type>.rst` for example (588.bugfix.rst)
  * `<type>` is must be one of `bugfix`, `feature`, `deprecation`, `breaking`, `doc`, `misc`
  * if PR has no issue: consider creating one first or change it to the PR number after creating the PR
  * "sign" fragment with ```-- by :user:`<your username>`.```
  * please, use full sentences with correct case and punctuation, for example:
    ```rst
    Fixed an issue with non-ascii contents in doctest text files -- by :user:`superuser`.
    ```
  * also see [examples](../tree/master/docs/changelog)
- [ ] added yourself to `CONTRIBUTORS` (preserving alphabetical order)
