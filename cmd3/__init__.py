import sys
sys.path.append("..")

import pkg_resources  # part of setuptools
__version__ = pkg_resources.require("cmd3")[0].version

