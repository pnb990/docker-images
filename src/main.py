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

from config import Config, ConfigError
from libs_path import add_libs_dir
from logging_config import configure_log

log = logging.getLogger(__name__)

TEMPLATES_DIR = "ressources/templates"


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


def render_variant(env, config, spec):
    """
    Render one Dockerfile: the skeleton, then the features in order
    Args:
        env (Environment): jinja environment
        config (Config): configuration object
        spec (dict): image_name, variant, base_image and ordered features
    Returns:
        str: content of the Dockerfile
    """
    body = "\n".join(
        env.get_template(config.features[feature]).render()
        for feature in spec["features"]
    )

    content = env.get_template("dockerfile.j2").render(
        body=body.rstrip("\n"), **spec
    )

    return content.rstrip("\n") + "\n"


def build_images(config, outdir):
    """
    build images from configuration
    Args:
        config (Config): configuration object
        outdir (Path): output directory
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        trim_blocks=True,
        keep_trailing_newline=True,
    )

    # A variant that disappears from the configuration must disappear from
    # images/ too, otherwise the build workflow keeps publishing it.
    for stale in outdir.glob("*.Dockerfile"):
        stale.unlink()

    images_list = []

    for i_name, image in config.images.items():
        for v_name, features in image.variants.items():
            spec = {
                "image_name": i_name,
                "variant": v_name,
                "base_image": image["from"],
                "features": list(features),
            }
            try:
                content = render_variant(env, config, spec)
            except TemplateNotFound as error:
                log.error(
                    "Template not found for image:%s variant:%s error:%s",
                    i_name,
                    v_name,
                    error,
                )
                sys.exit(1)
            except ConfigError as error:
                log.error(
                    "Unknown feature in image:%s variant:%s error:%s",
                    i_name,
                    v_name,
                    error,
                )
                sys.exit(1)

            file_name = f"{i_name}.{v_name}.Dockerfile"
            (outdir / file_name).write_text(content, encoding="utf-8")
            log.info(
                "Generated image:%s variant:%s features:%s",
                i_name,
                v_name,
                " -> ".join(spec["features"]),
            )
            images_list.append(
                {"name": i_name, "variant": v_name, "file": file_name}
            )

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
        help="configuration file; -c with no value reads $APP_CONFIG_FILE",
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
