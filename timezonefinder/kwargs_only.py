# -*- coding:utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
from functools import wraps


def kwargs_only(func):
    """
    Make a function only accept keyword arguments.
    This can be dropped in Python 3 in lieu of:
        def foo(*, bar=default):
    """
    if hasattr(inspect, 'signature'):  # pragma: no cover
        # Python 3
        signature = inspect.signature(func)
        first_arg_name = list(signature.parameters.keys())[0]
    else:  # pragma: no cover
        # Python 2
        signature = inspect.getargspec(func)
        first_arg_name = signature.args[0]

    if first_arg_name in ('self', 'cls'):
        allowable_args = 1
    else:
        allowable_args = 0

    @wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > allowable_args:
            raise TypeError("{} should only be called with keyword args".format(func.__name__))
        return func(*args, **kwargs)

    return wrapper
