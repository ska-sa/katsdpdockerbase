#!/usr/bin/env python
"""
Install a list of requirements from a requirements file. This is a shim around
pip that handles a few details:

- It only installs the exact list of packages provided. If these have
  dependencies not listed, the installation will fail.
- A second file may be used to specify default version specs for packages
  specified without any version spec.
- Every package must have an exact version specified.
- It knows about setup-time requirements that some packages neglect to
  declare, and performs several phases of installation.
"""

from __future__ import division, print_function, absolute_import, unicode_literals
import sys
import re
import argparse
import warnings
import codecs
import copy
import tempfile
import itertools
import subprocess
from six.moves import urllib

import six
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name


COMMENT_RE = re.compile(r'(^|\s)+#.*$')

# Packages in each epoch are installed with one pip command, before moving
# on to the next epoch. The default epoch is 0.  NB: use lowercase here, even
# if the canonical name for the package is uppercase.
EPOCH = {
    # Having up-to-date versions early allows wheel caching
    'pip': -100,
    'setuptools': -100,
    'wheel': -100,
    # Setup dependency for numerous other packages
    'numpy': -50,
    'cython': -50,
    'cffi': -50,
    'enum34': -50,   # Needed by llvmlite
    'katversion': -50,
    'git+ssh://git@github.com/ska-sa/katversion': -50,
    'pkginfo': -51,  # Needed by katversion
    # Has a lot of setup dependencies
    'mplh5canvas': 50,
    # Has setup dependencies, and doesn't properly declare its own dependencies
    'astro-tigger': 50
}


def parse_requirement(requirement):
    """Parse a single requirement.

    It will handle
    - requirements handled by packaging.requirements.Requirement
    - URLs, which are turned into PEP 508 URL specifications (using the #egg
      fragment to identify the package).

    Anything not handled is returned as a string (with a warning).

    >>> parse_requirement('requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"')
    <Requirement('requests[security,tests]==2.8.*,>=2.8.1; python_version < "2.7"')>
    >>> parse_requirement('https://github.com/pypa/pip/archive/1.3.1.zip#egg=pip')
    <Requirement('pip@ https://github.com/pypa/pip/archive/1.3.1.zip#egg=pip')>
    >>> parse_requirement('git+ssh://git@github.com/ska-sa/katdal')
    <Requirement('katdal@ git+ssh://git@github.com/ska-sa/katdal')>
    >>> parse_requirement('--no-binary :all:')
    '--no-binary :all:'

    Returns
    -------
    :class:`packaging.requirements.Requirement` or str
        The parsed requirement
    """
    try:
        return Requirement(requirement)
    except ValueError:
        if '://' not in requirement:
            warnings.warn('Requirement {} could not be parsed and is not an URL'
                          .format(requirement))
            return requirement
        url = urllib.parse.urlparse(requirement)
        frag_params = urllib.parse.parse_qs(url.fragment)
        if 'egg' in frag_params:
            name = frag_params['egg'][0]
        else:
            name = url.path.split('/')[-1]
        requirement = name + ' @ ' + requirement
        return Requirement(requirement)


def parse_requirements(filename):
    """Parse a requirements file.

    Comments are stripped, and the remaining non-blank lines are passed
    through :func:`parse_requirement`.
    """
    with codecs.open(filename, encoding='utf-8') as f:
        for line in f:
            line = COMMENT_RE.sub('', line)
            line = line.strip()
            if line:
                yield parse_requirement(line)


def make_requirements(args):
    """Split up requirements by epoch.

    Parameters
    ----------
    args : argparse.Namespace
        Command-line arguments

    Returns
    -------
    requirements : list of lists
        Each list corresponds to one epoch, with the epochs in order
    """
    reqs = []
    for requirements_file in args.requirements:
        reqs.append(parse_requirements(requirements_file))
    reqs.append([parse_requirement(req) for req in args.package])
    # Convert from list of iterables to an iterable
    reqs = itertools.chain(*reqs)
    defaults = []
    for default_versions in args.default_versions:
        defaults.extend(parse_requirements(default_versions))
    # Convert defaults from a list to a dictionary
    default_for = {}
    for item in defaults:
        if isinstance(item, Requirement):
            if item.marker and not item.marker.evaluate():
                continue
            name = canonicalize_name(item.name)
            pin = None
            for spec in item.specifier:
                if spec.operator in {'==', '==='}:
                    pin = spec
            if pin is not None:
                if name in default_for and default_for[name] != pin:
                    raise KeyError('{} is listed twice in {} with conflicting versions'
                                   .format(name, args.default_versions))
                default_for[name] = pin

    by_epoch = {}
    for item in reqs:
        if isinstance(item, Requirement):
            if item.marker and not item.marker.evaluate():
                continue
            pinned = (item.url is not None)
            name = canonicalize_name(item.name)
            for spec in item.specifier:
                if spec.operator in {'==', '==='}:
                    pinned = True
            if not pinned:
                if name not in default_for:
                    if not args.allow_unversioned:
                        raise RuntimeError('{} is not version-pinned'.format(name))
                else:
                    pin = default_for[name]
                    item = copy.deepcopy(item)
                    item.specifier &= SpecifierSet(six.text_type(pin))
            value = six.text_type(item)
        else:
            name = item
            value = item
        epoch = EPOCH.get(name, 0)
        by_epoch.setdefault(epoch, []).append(value)
    return [by_epoch[x] for x in sorted(by_epoch.keys())]


def run_pip(args, dry_run):
    if dry_run:
        print('pip {}'.format(' '.join(args)))
        if args != ['check']:
            print('Contents of {}:'.format(args[-1]))
            with codecs.open(args[-1], encoding='utf-8') as f:
                sys.stdout.write(f.read())
    else:
        ret = subprocess.call(['pip'] + args)
        if ret:
            sys.exit(ret)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--allow-unversioned', action='store_true',
        help='Do not complain if requirements do not have an exact version specified')
    parser.add_argument(
        '--default-versions', '-d', type=str, action='append', default=[],
        help='Requirements file that is consulted for unversioned requirements')
    parser.add_argument(
        '--requirements', '-r', type=str, action='append', default=[],
        help='Requirements file')
    parser.add_argument(
        '--dry-run', '-n', action='store_true',
        help='Just report what would be done')
    parser.add_argument(
        'package', type=parse_requirement, nargs='*',
        help='Extra requirements')
    args, extra_args = parser.parse_known_args()

    req = make_requirements(args)
    for epoch in req:
        with tempfile.NamedTemporaryFile('w', suffix='.txt') as req_file:
            for item in epoch:
                print(item, file=req_file)
            req_file.flush()
            run_pip(['install',
                     '--retries', '10', '--timeout', '30',
                     '--no-deps', '-r', req_file.name] + extra_args, args.dry_run)
    # Check that all dependencies were found
    run_pip(['check'], args.dry_run)

if __name__ == '__main__':
    sys.exit(main())
