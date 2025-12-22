#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Main command line entry point
"""

import argparse
import json
import logging
import os
import sys
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
            f"input:{prospective_file} is not a valid file"
        )
    if not os.access(prospective_file, os.R_OK):
        raise argparse.ArgumentTypeError(
            f"input:{prospective_file} is not readable"
        )
    return prospective_file


def output_dir(prospective_dir):
    """
    argparse output_dir validator
    """
    if not os.path.exists(prospective_dir):
        os.makedirs(prospective_dir)
    if not os.path.isdir(prospective_dir):
        raise argparse.ArgumentTypeError(
            f"output_dir:{prospective_dir} is not a valid path"
        )
    if not os.access(prospective_dir, os.W_OK):
        raise argparse.ArgumentTypeError(
            f"output_dir:{prospective_dir} is not writable"
        )
    if not os.access(prospective_dir, os.R_OK):
        raise argparse.ArgumentTypeError(
            f"output_dir:{prospective_dir} is not readable"
        )
    return prospective_dir


def build_images(config, outdir):
    """
    build images from configuration
    Args:
        config (Config): configuration object
        outdir (Path): output directory
    """
    env = Environment(loader=FileSystemLoader("ressources/templates"))

    images_list = []

    for i_name, image in config.images.items():
        try:
            for v_name, variant in config.variants.items():
                template = env.get_template(image.template)

                dev_rendered = template.render(
                    parent=str(variant.parent), base_image=str(variant.image)
                )

                file_path = outdir / f"{i_name}.{v_name}.Dockerfile"
                file_path.write_text(dev_rendered)
                log.info("Generated image:%s variant %s", i_name, v_name)
                images_list.append(f"{i_name}.{v_name}.Dockerfile")
        except TemplateNotFound as error:
            log.error(
                "Template not found for image:%s error:%s", i_name, error
            )
            sys.exit(1)

    with open(
        outdir / "images_list.json", "w", encoding="utf-8"
    ) as img_list_file:
        json.dump(images_list, img_list_file, indent=4)


def main(argv=None):
    """
    command line entry
    """

    add_libs_dir(["libs", "libs_ext", "config"])

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c",
        "--config",
        metavar="config file",
        nargs="?",
        type=readable_file,
        help="configuration file" "environment variable or ",
        default="config/default/config.yaml",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="output directory",
        nargs="?",
        type=output_dir,
        help="output directory",
        default="images",
    )

    args = parser.parse_args(argv)

    outdir = Path(args.output_dir)

    log.info("configuration loading from %s", args.config)
    config = Config(
        file=args.config if args.config else os.environ.get("APP_CONFIG_FILE")
    )
    configure_log(level=config.logs.level)

    build_images(config, outdir)


if __name__ == "__main__":
    main()
