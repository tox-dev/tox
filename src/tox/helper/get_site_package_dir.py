from __future__ import unicode_literals

import sysconfig
import json
import sys

data = json.dumps({"dir": sysconfig.get_path("purelib", vars={"base": sys.argv[1]})})
print(data)
