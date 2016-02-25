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

from __future__ import print_function, unicode_literals
import sys
import pkg_resources
import re
import argparse
import warnings
import codecs
import tempfile
import itertools
import subprocess

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
    'git+ssh://git@github.com/ska-sa/katversion': -50,
    # Has a lot of setup dependencies
    'mplh5canvas': 50
}

def parse_requirement(requirement):
    try:
        return pkg_resources.Requirement.parse(requirement)
    except ValueError:
        if '://' not in requirement:
            warnings.warn('Requirement {} could not be parsed and is not an URL'.format(requirement))
        return requirement

def parse_requirements(filename):
    """Parse a requirements file for lines that contain requirements that
    can be parsed by pkg_resources.Requirement.parse. Any lines that cannot
    be parsed in this way are returned as-is (although comments are removed).
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
    reqs.append(args.package)
    # Convert from list of iterables to an iterable
    reqs = itertools.chain(*reqs)
    defaults = []
    for default_versions in args.default_versions:
        defaults.extend(parse_requirements(default_versions))
    # Convert defaults from a list to a dictionary
    default_for = {}
    for item in defaults:
        if isinstance(item, pkg_resources.Requirement):
            pin = None
            for (op, version) in item.specs:
                if op == '==' or op == '===':
                    pin = (op, version)
            if pin is not None:
                if item.key in default_for and default_for[item.key] != pin:
                    raise KeyError('{} is listed twice in {} with conflicting versions'.format(item.project_name, args.default_versions))
                default_for[item.key] = pin

    by_epoch = {}
    for item in reqs:
        if isinstance(item, pkg_resources.Requirement):
            pinned = False
            for (op, version) in item.specs:
                if op == '==' or op == '===':
                    pinned = True
            if not pinned:
                try:
                    (op, version) = default_for[item.key]
                    item = pkg_resources.Requirement.parse('{0}{1}{2[0]}{2[1]}'.format(
                        item, ',' if item.specs else '', default_for[item.key]))
                except KeyError:
                    if not args.allow_unversioned:
                        raise RuntimeError('{} is not version-pinned'.format(item.project_name))
            key = item.key
            value = unicode(item)
        else:
            key = item
            value = item
        epoch = EPOCH.get(key, 0)
        by_epoch.setdefault(epoch, []).append(value)
    return [by_epoch[x] for x in sorted(by_epoch.keys())]

def run_pip(args, dry_run):
    if dry_run:
        print('pip {}'.format(' '.join(args)))
        print('Contents of {}:'.format(args[-1]))
        with codecs.open(args[-1], encoding='utf-8') as f:
            sys.stdout.write(f.read())
    else:
        ret = subprocess.call(['pip'] + args)
        if ret:
            sys.exit(ret)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-unversioned', action='store_true', help='Do not complain if requirements do not have an exact version specified')
    parser.add_argument('--default-versions', '-d', type=str, action='append', default=[], help='Requirements file that is consulted for unversioned requirements')
    parser.add_argument('--requirements', '-r', type=str, action='append', default=[], help='Requirements file')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Just report what would be done')
    parser.add_argument('package', type=parse_requirement, nargs='*', help='Package names')
    args = parser.parse_args()

    req = make_requirements(args)
    for epoch in req:
        with tempfile.NamedTemporaryFile(suffix='.txt') as req_file:
            for item in epoch:
                print(item, file=req_file)
            req_file.flush()
            run_pip(['install', '--no-deps', '-r', req_file.name], args.dry_run)
    # Check that all dependencies were found
    with tempfile.NamedTemporaryFile(suffix='.txt') as req_file:
        for epoch in req:
            for item in epoch:
                print(item, file=req_file)
        req_file.flush()
        run_pip(['install', '--no-cache', '--no-index', '--quiet', '-r', req_file.name], args.dry_run)

if __name__ == '__main__':
    sys.exit(main())
