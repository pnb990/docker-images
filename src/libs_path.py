#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause.txt

"""
Import library in ./lib ./lib_ext etc ...
"""

from typing import List
import sys
from pathlib import Path


def get_top_dir():
    """ Return the top directory path """
    return Path(__file__).parent.parent


def add_libs_dir(libs_dir: List[str]) -> None:
    """ Return the libs directory path """

    top_dir = get_top_dir()
    for lib_dir in libs_dir:
        sys.path.append(str(top_dir / lib_dir))
