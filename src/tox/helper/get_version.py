from __future__ import unicode_literals

import json
import sys

info = {
    "executable": sys.executable,
    "version_info": list(sys.version_info),
    "version": sys.version,
    "sysplatform": sys.platform,
}
info_as_dump = json.dumps(info)
print(info_as_dump)
