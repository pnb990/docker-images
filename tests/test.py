#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Testing module
"""

import json
import logging
import os
import subprocess
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

try:
    import pycodestyle
    import pylint
    from pylint import lint
    from pylint.reporters import CollectingReporter
except ImportError as error:
    MSG = f"missing dependency do :\n$ uv sync --dev\nerror :{error}"
    print(MSG)
    log = logging.getLogger()
    log.error(MSG)
    sys.exit(1)

TOP_DIR = Path(__file__).parents[1]
show_todo = False

# Set log level
logging.getLogger().setLevel(os.environ.get("LOGLEVEL", "WARNING").upper())
# Show debug log level in text
LOG_LEVEL_NAME = logging.getLevelName(logging.getLogger().getEffectiveLevel())
print(f"Set log level to {LOG_LEVEL_NAME}")
# Configure global logger with colors
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


log = logging.getLogger(__name__)


def get_excluded():
    """
    List of directories to exclude from tests
    """
    excluded = []
    exclude_file = TOP_DIR / "tests" / "lint_exclude.txt"

    with open(exclude_file, "r", encoding="utf-8") as fd:
        for line in fd:
            line = line.strip()
            if line and not line.startswith("#"):
                excluded.append(TOP_DIR / line)

    return excluded


def get_git_ignored(paths):
    """
    Subset of paths that git ignores.

    Whatever .gitignore already covers (virtualenvs, build output, ...) does
    not have to be repeated in lint_exclude.txt.
    """
    if not paths:
        return set()

    try:
        result = subprocess.run(
            ["git", "-C", str(TOP_DIR), "check-ignore", "-z", "--stdin"],
            input="\0".join(map(str, paths)),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        log.warning("git unavailable, .gitignore not applied: %s", error)
        return set()

    # 0: some paths are ignored, 1: none of them, the rest is a failure
    # (no repository, no git, ...) and must not silently drop every file.
    if result.returncode not in (0, 1):
        log.warning("git check-ignore failed: %s", result.stderr.strip())
        return set()

    return {Path(line) for line in result.stdout.split("\0") if line}


class TestCodeFormat(unittest.TestCase):
    """
    Test code style and coding rules.
    """

    def setUp(self):
        """
        setup test by create list of all file tested
        """
        self.tested_pyfiles = []

        excluded_list = get_excluded()

        pyfiles = list(TOP_DIR.rglob("*.py"))
        git_ignored = get_git_ignored(pyfiles)

        for name in pyfiles:
            ignore = False

            name = Path(name)
            basename = name.name.lower()

            # Skip __init__.py files
            if basename == "__init__.py":
                ignore = True

            # Skip whatever git ignores
            if name in git_ignored:
                ignore = True

            # Skip any excluded directories
            for excluded in excluded_list:
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
            print("TODO disabled (w0511)")
            pylint_opts.append("--disable=W0511")
        result = lint.Run(pylint_opts, reporter=report, exit=False)

        note = result.linter.stats.global_note

        line_format = "{path}:{line}:{column}: {msg_id}: {msg} ({symbol})"
        for msg in report.messages:
            print(line_format.format(**asdict(msg)))

        print(f"pylint note: {note}")
        self.assertGreaterEqual(
            note, 10, f"pylint note is not enough {note:.4f} < 10.0"
        )

    def test_pyright(self):
        """
        Check that scripts are pyright compliant (type checking).
        """

        result = subprocess.run(
            ["pyright", "--outputjson"] + list(map(str, self.tested_pyfiles)),
            capture_output=True,
            text=True,
            check=False,
        )

        data = json.loads(result.stdout)
        error_count = data["summary"]["errorCount"]

        for diag in data.get("generalDiagnostics", []):
            if diag["severity"] == "error":
                line = diag["range"]["start"]["line"] + 1
                col = diag["range"]["start"]["character"] + 1
                print(f"{diag['file']}:{line}:{col}: error: {diag['message']}")

        self.assertEqual(
            error_count, 0, f"pyright found {error_count} error(s)"
        )


# Executing the tests in the above test case class
if __name__ == "__main__":

    print("uv run python3 -m unittest discover tests")
    print(f"pylint version      {pylint.__version__}")
    print(f"pycodestyle version {pycodestyle.__version__}")

    if "-t" in sys.argv:
        sys.argv.remove("-t")
        show_todo = True

    log.debug("*" * 80)
    log.debug("*" * 80)
    log.debug("*" * 80)
    log.debug("*" * 80)
    log.debug("*" * 80)
    log.debug("*" * 80)

    unittest.main()
