#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause.txt

"""
Configuration library
"""

import logging
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


def yaml_include_constructor(loader, node):
    """
    YAML include hook implementation
    """

    filename = Path(loader.stream.name).parent / loader.construct_scalar(node)

    with open(filename, 'r', encoding='utf-8') as file:
        return yaml.load(file, type(loader))


def yaml_file_to_str_constructor(loader, node):
    """
    YAML include string file hook implementation
    """

    filename = loader.construct_scalar(node)

    with open(filename, 'r', encoding='utf-8') as loaded_file:
        data = loaded_file.read()
        return f'"{data}"'


yaml.add_constructor('!include',      yaml_include_constructor)
yaml.add_constructor('!file_to_str',  yaml_file_to_str_constructor)


class ConfigError(Exception):
    """ Configuration error """


class ConfigNode:
    """ Configuration class """
    def __init__(self, name, parent=None, data=None, default=None):
        self._default = default or {}
        self.name = name
        self.parent = parent
        self._data = data or {}

    def set_default(self, default):
        """ Set default value data """
        self._default = default
        for name, val in self._default.items():
            if name not in self._data:
                self._data[name] = val

    def __name__(self):
        return self.name

    def __str__(self):
        """ Convert configuration node to string """
        return f"ConfigNode path:{self.path}"

    def __iter__(self):
        """ Iterate over configuration node key/values """
        value = self._data
        if not value:
            value = self._default

        if isinstance(value, dict):
            return iter(value)

        if isinstance(value, list):
            return iter(value)

        raise ConfigError(f"Cannot iterate over {self}")

    def items(self):
        """ Iterate over configuration node key/values """
        value = self._data
        if not value:
            value = self._default

        if isinstance(value, dict):
            def dict_iterator(content):
                for name, value in content.items():
                    if isinstance(value, dict):
                        value = ConfigNode(name, self, data=value)
                    yield name, value
            return dict_iterator(value)

        raise ConfigError(f"Cannot iterate over {self}")

    @property
    def path(self):
        """ Get path to configuration node """
        path = []
        cfgnode = self
        while cfgnode is not None:
            path.insert(0, cfgnode.name)
            cfgnode = cfgnode.parent
        return "/".join(path)

    def to_dict(self):
        """ convert configuration node key/value to dict """
        _dict = {}
        for name, val in self._default.items():
            _dict[name] = val
        for name, val in self._data.items():
            _dict[name] = val
        return _dict

    def get(self, name, default=None):
        """
        Get configuration value of name
        """
        try:
            return getattr(self, name)
        except ConfigError:
            return default

    def __getattr__(self, name):
        """ Give configuration of name """
        try:
            val = self._data.get(name, None)
            if val is None:
                # if no default value, raise KeyError
                val = self._default[name]
            if isinstance(val, dict):
                val = ConfigNode(name,
                                 self,
                                 data=val,
                                 default=self._default.get(name)
                                 )
        except KeyError as error:
            raise ConfigError(f"Invalid attribute '{name}' for {self}"
                              ) from error
        return val


class Config(ConfigNode):
    """ Configuration class """
    def __init__(self, file):
        self._data = {}
        self._default = {}
        self._file = Path(file).expanduser()
        if not self._file.is_file():
            log.warning("Configuration file '%s' does not exist", self._file)
        super().__init__(name="")
        self.load()

    def load(self, file=None):
        """ load configuration """
        try:
            if file is not None:
                self._file = file

            with open(self._file, encoding='utf-8') as fd:
                self._data = yaml.full_load(fd)

        except (yaml.YAMLError, FileNotFoundError) as error:
            log.error("Failed to load '%s': %s", self._file, error)
            self._data = {}

    def save(self):
        """ Save configuration """
        with open(self._file, "w", encoding='utf-8') as file:
            yaml.dump(self._data, file, indent=4)
