Close the freshly opened pseudo-terminal file descriptors when copying terminal attributes to the child fails, instead
of leaking both descriptors on that error path.
