#
#  Copyright (c) 2015 - 2024, Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#

try:
    from .version import version as __version__
    from .version import version_tuple as __version_tuple__
except ImportError:
    try:
        from setuptools_scm import get_version
        __version__ = get_version('..')
    except ImportError:
        __version__ = '0.0.0'
