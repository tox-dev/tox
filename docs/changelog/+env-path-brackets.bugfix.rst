When :ref:`work_dir` or :ref:`tox_root` contains ``[``, ``*`` or ``?``, tox now treats those characters literally in its
own executable paths and in default or relative :ref:`package_glob` patterns. This lets it run environment commands and
find packages built by ``package = external``.
