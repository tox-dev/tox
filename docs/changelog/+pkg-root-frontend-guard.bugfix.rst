Check the backing frontend field rather than the lazy ``_frontend`` property when reassigning a PEP 517 package
environment's ``root``, so swapping the root before a frontend exists no longer builds a throwaway frontend against
the previous root (which could fail if that root lacks a valid ``[build-system]``).
