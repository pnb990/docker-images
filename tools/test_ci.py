#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause.txt

"""
Testing module
"""

import sys
from pathlib import Path
import logging
from dataclasses import asdict

import unittest

try:
    import pycodestyle
    import pylint
    from pylint import lint
    from pylint.reporters import CollectingReporter
except ImportError as error:
    MSG = ("missing dependency do :\n"
           "$ pip install pycodestyle pylint\n"
           f"error :{error}"
           )
    print(MSG)
    log = logging.getLogger()
    log.error(MSG)

TOP_DIR = Path(__file__).parents[1]
show_todo = False

log = logging.getLogger(__name__)


class TestCodeFormat(unittest.TestCase):
    """
    Test code style and coding rules.
    """

    EXCLUDE_DIRS = [
        TOP_DIR / 'lib_ext',
    ]

    def setUp(self):
        """
        setup test by create list of all file tested
        """
        self.tested_pyfiles = []

        for name in TOP_DIR.rglob('*.py'):
            ignore = False

            name = Path(name)
            basename = name.name.lower()

            # Skip __init__.py files
            if basename == '__init__.py':
                ignore = True

            # Skip any excluded directories
            for excluded in self.EXCLUDE_DIRS:
                if excluded in name.parents:
                    ignore = True
                    break

            if not ignore:
                log.debug(name)
                self.tested_pyfiles.append(name)

    def test_pycodestyle(self):
        """
        Check that scripts are PEP-8 compliant.
        """
        style = pycodestyle.StyleGuide(quiet=False)
        result = style.check_files(self.tested_pyfiles)
        self.assertEqual(result.total_errors, 0, "Found style errors")

    def test_pylint(self):
        """
        Check that scripts are pylint compliant.
        """
        report = CollectingReporter()
        pylint_opts = list(map(str, self.tested_pyfiles))
        if not show_todo:
            print('TODO disabled (w0511)')
            pylint_opts.append('--disable=W0511')
        result = lint.Run(pylint_opts, reporter=report, exit=False)

        note = result.linter.stats.global_note

        line_format = "{path}:{line}:{column}: {msg_id}: {msg} ({symbol})"
        for msg in report.messages:
            print(line_format.format(**asdict(msg)))

        self.assertGreater(note, 9.99, f"pylint note is not enough {note:0.2}")


# class TestSomething(unittest.TestCase):
#     """
#     Test for Something class
#     """
#
#     def setUp(self):
#         """
#         setUp method is overridden from the parent class TestCase
#         """
#         pass
#
#     def test_(self):
#         """
#         Each test method starts with the keyword test_
#         """
#         pass

# Executing the tests in the above test case class
if __name__ == "__main__":

    print(f"pylint version      {pylint.__version__}")
    print(f"pycodestyle version {pycodestyle.__version__}")

    if '-t' in sys.argv:
        sys.argv.remove('-t')
        show_todo = True

    log.debug("*"*80)
    log.debug("*"*80)
    log.debug("*"*80)
    log.debug("*"*80)
    log.debug("*"*80)
    log.debug("*"*80)

    unittest.main()
