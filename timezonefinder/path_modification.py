# -*- coding:utf-8 -*-
"""modify pythonpath to make timezonefinder package discoverable."""

import sys
from os.path import pardir

sys.path.insert(0, pardir)
