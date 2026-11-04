A pair of numbers after a ``-`` is no longer read as a range, so ``py-django-4-2`` keeps its name instead of splitting
into ``py-django-4``, ``3`` and ``2``. Braced ranges such as ``py-django-{4-5}`` still expand.
