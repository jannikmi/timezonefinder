# -*- coding:utf-8 -*-
"""modify pythonpath to make parent package discoverable."""

import sys
from os.path import pardir

sys.path.insert(0, pardir)


def dummy_fct():
    pass
