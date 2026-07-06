Fix ``Config.__contains__`` to compare environment names directly instead of testing the matched name's truthiness,
so an environment whose name is an empty string is reported as present.
