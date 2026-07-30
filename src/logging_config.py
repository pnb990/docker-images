#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Testing module
"""

import logging

try:
    import colorlog

    FORMAT = (
        "%(log_color)s%(levelname)-8s%(asctime)s "
        "{%(name)-32s:%(lineno)4d}"
        "%(reset)s %(message)s"
    )

    FORMATER = colorlog.ColoredFormatter(
        fmt=FORMAT,
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        style="%",
    )

    HANDLER = logging.StreamHandler()
    HANDLER.setFormatter(FORMATER)
    colorlog.getLogger().addHandler(HANDLER)

except ImportError as error:
    FORMAT = "%(levelname)-8s[%(asctime)s] %(message)s"
    logging.basicConfig(format=FORMAT)
    MSG = (
        "colorlog is not installed if you want color do :\n"
        "$ sudo aptitude install python3-colorlog\n"
        "or\n"
        "$ pip install colorlog\n"
        f"error :{error}"
    )
    log = logging.getLogger()
    log.info(MSG)
    print(MSG)


def configure_log(level: int | str | None = logging.INFO) -> None:
    """
    Configure logging, color format
    parameters:
    - level : logging level name, or verbosity count when given as an int
    """

    if level is None:
        return

    if isinstance(level, int):
        lvls = [logging.ERROR, logging.INFO, logging.DEBUG]
        if level >= len(lvls):
            level = len(lvls) - 1
        level = lvls[level]

    logging.getLogger().setLevel(level)
