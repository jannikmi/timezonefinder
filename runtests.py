#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)
import os
import sys

import pytest


def main():
    sys.path.insert(0, "test")
    return pytest.main()


if __name__ == '__main__':
    # run test for in_memory=False
    res = main()
    if res != 0:
        sys.exit(res)

    # run test for in_memory=True
    os.environ['IN_MEMORY_MODE'] = '1'
    res = main()

    sys.exit(res)
