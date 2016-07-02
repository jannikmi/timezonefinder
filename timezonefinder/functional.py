# -*- encoding:utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
from functools import wraps


def kwargs_only(func):
    """
    Make a function only accept keyword arguments.

    This can be dropped in Python 3 in lieu of:

        def foo(*, bar=default):
    """
    signature = inspect.getargspec(func)

    if signature.args[:1] in (['self'], ['cls']):
        allowable_args = 1
    else:
        allowable_args = 0

    @wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > allowable_args:
            raise TypeError("{} should only be called with keyword args".format(func.__name__))
        return func(*args, **kwargs)

    return wrapper
