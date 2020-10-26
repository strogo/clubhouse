#!/usr/bin/env python3
#
# Copyright © 2020 Endless OS Foundation LLC.
#
# This file is part of clubhouse
# (see https://github.com/endlessm/clubhouse).
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

# Tool to build and install a Flatpak containing all the Hack modules.

import argparse
import configparser
import functools
import json
import os
import re
import shutil
import string
import subprocess
import sys

import http.client

# Not all our modules are private, but since some are and we build all
# of them, we use the private GitHub URL:
GIT_URL_TEMPLATE = 'https://github.com/endlessm/{}.git'

DEFAULTS = {
    'Common': {
        'install': True,
        'bundle': False,
        'stable': False,
        'offline': False,
        'add-commit': False,
        'template-branch': '@BRANCH@',
        'template-modules-branch': '@BRANCH@',
    },
    'Advanced': {
        'repo': 'repo',
        'branch': '',
        'extra_build_options': '',
        'extra_install_options': '',
    },
}


class BuildError(Exception):
    pass


class Config:
    def __init__(self, config_file, example_file=None, defaults=None, flatpak_branch=None):
        dst_config = os.path.join('katamari', config_file)
        if example_file is None:
            example_file = os.path.join('katamari', 'data', config_file + '.example')

        # If a config file doesn't exist, create it:
        if not os.path.exists(dst_config):
            shutil.copyfile(example_file, dst_config)

        self._config = configparser.ConfigParser()
        self._config.read(dst_config)

        if defaults is None:
            self._defs = DEFAULTS
        else:
            self._defs = defaults

        # flatpak_branch overrides the default and file configuration and
        # forces to use this value
        if flatpak_branch:
            self._config['Advanced']['branch'] = flatpak_branch

    @functools.lru_cache(maxsize=None)
    def get(self, section, key):
        if section not in self._config:
            return self._defs[section][key]

        if isinstance(self._defs[section][key], bool):
            method_name = 'getboolean'
        else:
            method_name = 'get'

        method = getattr(self._config[section], method_name)
        return method(key, self._defs[section][key])

    def get_default_branch(self):
        return 'eos3' if self.get('Common', 'stable') else 'master'

    def get_flatpak_branch(self):
        # First, check if there is an override in the advanced
        # settings:
        advanced_branch = self.get('Advanced', 'branch')
        if advanced_branch:
            return advanced_branch

        if 'Modules' in self._config and len(self._config['Modules']):
            return 'custom'

        return self.get_default_branch()

    def get_flatpak_build_options(self):
        repo = self.get('Advanced', 'repo')
        flatpak_builder_options = ['--force-clean', '--repo=' + repo]

        if self.get('Common', 'offline'):
            flatpak_builder_options.append('--disable-download')

        extra_build_options = self.get('Advanced', 'extra_build_options')
        if extra_build_options:
            flatpak_builder_options.extend(extra_build_options.split())

        return flatpak_builder_options

    def get_flatpak_install_options(self):
        flatpak_install_options = ['--reinstall']

        if self.get('Common', 'offline'):
            flatpak_install_options.append('--no-deps')

        extra_install_options = self.get('Advanced', 'extra_install_options')
        if extra_install_options:
            flatpak_install_options.extend(extra_install_options.split())

        return flatpak_install_options

    def get_template_values(self, modules, template=None):
        template_values = {
            'BRANCH': self.get_flatpak_branch(),
        }

        modules_branch = self.get('Common', 'template-modules-branch')
        add_commit = self.get('Common', 'add-commit')
        default_git_branch = modules_branch if template else self.get_default_branch()

        for module in modules:
            source_key = _get_source_key(module)
            if 'Modules' in self._config and module in self._config['Modules']:
                module_value = self._config['Modules'][module]
                value = _get_source(module, module_value, default_git_branch, add_commit)
            else:
                default_git_url = _get_default_git_url(module)
                value = _get_git_source(default_git_url, default_git_branch)
                if add_commit:
                    value['commit'] = _get_git_commit(module, default_git_branch)

            template_values[source_key] = _pretty_print_source(value)

            # Per-module options:
            if module in self._defs:
                for option in self._defs[module]:
                    option_key = _get_option_key(module, option)
                    value = self.get(module, option)
                    if isinstance(value, str):
                        template_values[option_key] = value
                    else:
                        template_values[option_key] = json.dumps(value)

        return template_values

    def print_parsed_config(self):
        self._config.write(sys.stdout)


def _get_default_git_url(module):
    return GIT_URL_TEMPLATE.format(module)


def _get_source_key(module):
    return module.upper().replace('-', '_') + '_SOURCE'


def _get_option_key(module, option):
    return module.upper().replace('-', '_') + '_' + option.upper()


def _get_git_commit(module, branch):
    api = f'/repos/endlessm/{module}/git/ref/heads/{branch}'

    conn = http.client.HTTPSConnection("api.github.com")
    conn.request("GET", api, headers={'User-Agent': 'python script'})
    response = conn.getresponse()
    return json.loads(response.read())['object']['sha']


def _get_git_source(git_url, git_branch):
    return {
        'type': 'git',
        'url': git_url,
        'branch': git_branch,
    }


def _pretty_print_source(value, indent=4, offset=16):
    lines = json.dumps(value, indent=indent).split('\n')
    # First line keeps the default offset
    head = lines[:1]
    tail = [(' ' * offset) + line for line in lines[1:]]
    return '\n'.join(head + tail)


def _get_dir_source(directory):
    return {
        'type': 'dir',
        'path': directory,
        'skip': ['.flatpak-builder'],
    }


def _get_source(module, module_value, default_git_branch, add_commit=False):
    """Get source for module to embed it in the flatpak manifest.

    It guesses what module_value means. Examples:

    - Passing a git branch:

    >>> _get_source('clubhouse', 'mybranch', default_git_branch='master')
    {'type': 'git', 'url': 'ssh://git@github.com/endlessm/clubhouse.git', 'branch': 'mybranch'}

    - Passing a git url:

    >>> _get_source('clubhouse', 'https://my-repo.git', default_git_branch='master')
    {'type': 'git', 'url': 'https://my-repo.git', 'branch': 'master'}

    - Passing a git url plus a git branch:

    >>> _get_source('clubhouse', 'https://my-repo.git:mybranch', default_git_branch='master')
    {'type': 'git', 'url': 'https://my-repo.git', 'branch': 'mybranch'}

    - Passing a local directory (Note: don't pass your home dir! This
      is just for testing):

    >>> s = _get_source('clubhouse', '~/', default_git_branch='master')
    >>> s['type']
    'dir'

    >>> from os.path import expanduser
    >>> expanduser("~") == s['path']
    True

    """
    if module_value.endswith('.git'):
        # We assume the format is a git url:
        return _get_git_source(module_value, default_git_branch)

    full_path = os.path.abspath(os.path.expanduser(module_value))
    if os.path.isdir(full_path):
        # We assume the format is a local directory:
        return _get_dir_source(full_path)

    if ':' in module_value:
        # We assume the format is a git url:branch
        git_url, git_branch = module_value.rsplit(':', 1)
        return _get_git_source(git_url, git_branch)

    # At last we assume the format is a git branch for the default git
    # url.
    git_url = _get_default_git_url(module)
    source = _get_git_source(git_url, module_value)

    if add_commit:
        source['commit'] = _get_git_commit(module, default_git_branch)

    return source


def create_flatpak_manifest(config, modules, manifest, template=None):
    template_values = config.get_template_values(modules, template)

    manifest_file = manifest
    if template:
        template_values['BRANCH'] = config.get('Common', 'template-branch')
        manifest_file = template

    manifest_out = ''
    with open(manifest + '.in') as fd:
        template = string.Template(fd.read())
        manifest_out = template.substitute(template_values)
        # Removing comments to avoid problems with strict json
        manifest_out = re.sub(r'\s*\/\*\*.*\*\*\/', '', manifest_out)

    with open(manifest_file, 'w') as fd:
        fd.write(manifest_out)


def run_command(*args, **kwargs):
    p = subprocess.run(*args, **kwargs)
    if p.returncode != 0:
        raise BuildError('Error running: {}'.format(' '.join(p.args)))


def build_flatpak(manifest, flatpak_builder_options):
    run_command(['flatpak-builder', 'build', manifest] + flatpak_builder_options)


def install_flatpak(repo, flatpak_branch, app_id, flatpak_install_options):
    run_command(['flatpak', 'install'] +
                flatpak_install_options +
                ['./' + repo, app_id + '//' + flatpak_branch])


def build_bundle(repo, flatpak_branch, app_id, options=[]):
    run_command(['flatpak', 'build-bundle', repo, app_id + '.flatpak',
                 app_id, flatpak_branch, *options])


def print_error(message):
    sys.stderr.write('\x1b[1;31m' + 'Error: ' + message + '\x1b[0m' + '\n')


def run(main, *args, **kwargs):
    parser = argparse.ArgumentParser(description='Tool to build and install a Flatpak.')
    parser.add_argument('mode', nargs='?', choices=('print-config',),
                        metavar='MODE',
                        help='print-config: Print the parsed configuration.')
    parser.add_argument('--manifest-template',
                        help=('Only generates the flatpak template manifest'
                              ' in the desired location.'))
    cli_args = parser.parse_args()

    # Run this script in the base directory:
    source_dir = subprocess.check_output(
        ['/usr/bin/git', 'rev-parse', '--show-toplevel'],
        universal_newlines=True).strip()
    os.chdir(source_dir)

    config = Config(*args, **kwargs)

    if cli_args.mode == 'print-config':
        config.print_parsed_config()
        sys.exit()

    try:
        main(config, cli_args.manifest_template)
    except BuildError as error:
        sys.exit(error)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
