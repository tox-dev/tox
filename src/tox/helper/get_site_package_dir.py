from __future__ import unicode_literals

import json
import sys
import sysconfig

data = json.dumps({"dir": sysconfig.get_path("purelib", vars={"base": sys.argv[1]})})
print(data)
