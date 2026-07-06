Avoid crashing ``create_session_view`` with a ``ValueError`` when the package and its session copy share no common
base path (for example a package and workdir on different Windows drives); the shared path is now only used for the
debug log.
