#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause.txt

"""
Main command line entry point
"""

import argparse
import logging
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from config import Config
from libs_path import add_libs_dir
from logging_config import configure_log

log = logging.getLogger(__name__)


def readable_file(prospective_file):
    """
    argparse readable_file validator
    """
    if not os.path.isfile(prospective_file):
        raise argparse.ArgumentTypeError(
                f"input:{prospective_file} is not a valid file")
    if not os.access(prospective_file, os.R_OK):
        raise argparse.ArgumentTypeError(
                f"input:{prospective_file} is not readable")
    return prospective_file


def output_dir(prospective_dir):
    """
    argparse output_dir validator
    """
    if not os.path.exists(prospective_dir):
        os.makedirs(prospective_dir)
    if not os.path.isdir(prospective_dir):
        raise argparse.ArgumentTypeError(
                f"output_dir:{prospective_dir} is not a valid path")
    if not os.access(prospective_dir, os.W_OK):
        raise argparse.ArgumentTypeError(
                f"output_dir:{prospective_dir} is not writable")
    if not os.access(prospective_dir, os.R_OK):
        raise argparse.ArgumentTypeError(
                f"output_dir:{prospective_dir} is not readable")
    return prospective_dir


def main(argv=None):
    """
    command line entry
    """

    add_libs_dir(["libs", "libs_ext", "config"])

    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--config', metavar="config file",
                        nargs='?',
                        type=readable_file,
                        help='configuration file'
                        'environment variable or ',
                        default='config/default/config.yaml'
                        )

    parser.add_argument(
            '-o', '--output-dir',
            metavar="output directory",
            nargs='?',
            type=output_dir,
            help='output directory',
            default='out',
            )

    args = parser.parse_args(argv)

    config = Config(file=args.config
                    if args.config else os.environ.get("APP_CONFIG_FILE"))
    configure_log(level=config.logs.level)
    log.info("configuration loaded from %s", args.config)


    env = Environment(loader=FileSystemLoader("ressources/templates"))

    outdir = Path(args.output_dir)

    for name, image in config.images.items():
        try:
            template = env.get_template(image.template)

            # Generate Dockerfile for devcontainer
            dev_rendered = template.render(
                parent=config.common.base_template,
                base_image=config.common.base_image,
            )
            (outdir / f"{name}.devcontainer.Dockerfile").write_text(dev_rendered)

            # Generate Dockerfile for CI
            ci_rendered = template.render(
                parent=config.common.ci_template,
                base_image=config.common.base_image,
            )
            (outdir / f"{name}.ci.Dockerfile").write_text(ci_rendered)

            log.info("Generating Dockerfiles for image:%s", name)
        except TemplateNotFound as e:
            log.error("Template not found for image:%s error:%s", name, e)

if __name__ == "__main__":
    main()
