A requirements file whose declared encoding (PEP 263 coding cookie) cannot decode its content now raises a descriptive
error naming the file and the declared encoding, instead of surfacing a raw ``UnicodeDecodeError``.
