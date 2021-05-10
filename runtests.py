#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

import pytest


def main():
    sys.path.insert(0, "test")
    return pytest.main()


if __name__ == "__main__":
    sys.exit(main())
