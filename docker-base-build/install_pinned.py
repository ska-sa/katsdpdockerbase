#!/usr/bin/env python3
"""
Install a list of requirements from a requirements file. This is a shim around
pip that forces a version to be specified for every package installed, either
by explicitly installing a particular version or specifying a constraint for
it. However, VCS URLs are not required to use a tag/commit: any URL is valid.

Additionally, a new type of constraint file can be used by specifying
``--default-versions`` instead of `--constraint``: these are weaker than normal
constraints, in that they specify a default version but a normal requirement
or constraint can override it by specifying a different exact version.

It passes some additional arguments to ``pip`` to make it more suitable for use
in CI/CD pipelines.
"""

import argparse
import codecs
from collections import deque
import os
import re
import subprocess
import sys
import tempfile
from typing import Deque, Dict, List, Sequence, Union, Generator, Iterable
import urllib.parse
import urllib.request
import warnings

from packaging.markers import UndefinedEnvironmentName
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from pip._internal.req import InstallRequirement
from pip._vendor.packaging.requirements import Requirement as PipRequirement
import piptools.repositories.pypi


COMMENT_RE = re.compile(r'(^|\s)+#.*$')
RECURSIVE_FILE_RE = re.compile(r'^\s*-([rcd])\s+(.*)')

SKIP_PACKAGES = frozenset(['pip', 'setuptools'])


class Package:
    """A requirement specification plus extra data."""

    def __init__(self, requirement: Union[Requirement, str], *,
                 constraint: bool = False,
                 weak: bool = False) -> None:
        if isinstance(requirement, str):
            self.requirement = Requirement(requirement)
        else:
            self.requirement = requirement
        self.constraint = constraint
        self.weak = weak

    def __repr__(self):
        return f'Package({str(self.requirement)!r}, constraint={self.constraint}, weak={self.weak})'

    def _key(self):
        return (
            self.requirement.name,
            self.requirement.url,
            frozenset(self.requirement.extras),
            self.requirement.specifier,
            str(self.requirement.marker),
            self.constraint,
            self.weak
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Package):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())


class ResolutionError(RuntimeError):
    """resolve() failed."""

    def __init__(self, errors):
        super().__init__(f'Resolution failed with {len(errors)} error(s)')
        self.errors = errors


def has_exact(specifiers: SpecifierSet) -> bool:
    """Determine whether a specifier set pins an exact version."""
    return any(spec.operator in {'==', '==='} and '*' not in spec.version for spec in specifiers)


def parse_requirement(requirement: str, *,
                      constraint: bool = False, weak: bool = False) -> Union[Package, str]:
    """Parse a single requirement.

    It will handle
    - requirements handled by packaging.requirements.Requirement
    - command-line options, which are returned as-is.

    Anything not handled is returned as a string (with a warning).
    """
    try:
        req = Requirement(requirement)
    except ValueError:
        if not requirement.startswith('-'):
            warnings.warn('Requirement {} could not be parsed and is not an option'
                          .format(requirement))
        return requirement

    req.name = canonicalize_name(req.name)
    return Package(req, constraint=constraint, weak=weak)


def _is_url(path):
    return path.startswith('http://') or path.startswith('https://')


def _path_join(origin, path):
    if _is_url(path):
        return path
    elif _is_url(origin):
        return urllib.parse.urljoin(origin, path)
    else:
        return os.path.join(os.path.dirname(origin), path)


def _parse_requirements(stream, origin: str, *,
                        constraint: bool, weak: bool) \
        -> Generator[Union[Package, str], None, None]:
    for line in stream:
        line = COMMENT_RE.sub('', line)
        line = line.strip()
        if not line:
            continue
        match = RECURSIVE_FILE_RE.fullmatch(line)
        if match:
            path = _path_join(origin, match.group(2))
            yield from parse_requirements(
                path,
                constraint=(match.group(1) != 'r'),
                weak=(match.group(1) == 'd')
            )
        else:
            yield parse_requirement(line, constraint=constraint, weak=weak)


def parse_requirements(filename: str, *,
                       constraint: bool = False, weak: bool = False) \
        -> Generator[Union[Package, str], None, None]:
    """Parse a requirements file.

    Comments are stripped, ``-c`` and ``-r`` options are handled recursively,
    and the remaining non-blank lines are passed through
    :func:`parse_requirement`.
    """
    if _is_url(filename):
        with urllib.request.urlopen(filename) as raw:
            # This is quick-n-dirty; using a proper library like requests
            # would determine the charset from the content type.
            with codecs.getreader('utf-8')(raw) as enc:
                yield from _parse_requirements(enc, filename, constraint=constraint, weak=weak)
    else:
        with open(filename) as f:
            yield from _parse_requirements(f, filename, constraint=constraint, weak=weak)


def merge_packages(pkg1: Package, pkg2: Package) -> Package:
    """Combine two requirements for the same package."""
    # Simplify some of the logic by ensuring that if one is weak and one is
    # strong, the strong one is first.
    if pkg1.weak and not pkg2.weak:
        pkg1, pkg2 = pkg2, pkg1

    req1 = pkg1.requirement
    req2 = pkg2.requirement
    if req1.name != req2.name:
        raise ValueError(f'Cannot merge requirements with different names: {req1} vs {req2}')
    # If either requirement is inapplicable because of a marker, just ignore it.
    if req1.marker and not req1.marker.evaluate():
        return pkg2
    if req2.marker and not req2.marker.evaluate():
        return pkg1
    if req1.url is not None and req2.url is not None and req1.url != req2.url:
        if pkg1.weak == pkg2.weak:
            raise ValueError(f'Cannot merge requirements with inconsistent URLs: {req1} vs {req2}')
    new_req = Requirement(str(req1))
    new_req.extras |= req2.extras
    # Strong specifier only replaces weak if it has an exact version pinned
    if pkg1.weak == pkg2.weak or not has_exact(new_req.specifier):
        new_req.specifier &= req2.specifier
    if req1.url is None and req2.url is not None:
        new_req.url = req2.url
    # Cannot have both URL and specifiers. Assume URLs represent some
    # infinitely high version number, so that they always satisfy >=
    # specifiers but not others.
    if new_req.url is not None:
        for spec in new_req.specifier:
            if '999999999' not in spec:
                raise ValueError(f'Cannot combine URL {new_req.url!r} with specifier {spec}')
        new_req.specifier = SpecifierSet('')
    return Package(new_req, constraint=pkg1.constraint and pkg2.constraint, weak=pkg1.weak)


def version_from_requirement(requirement: Requirement) -> str:
    if requirement.url is not None:
        raise ValueError('Cannot get version from an URL requirement')
    pin = None
    for spec in requirement.specifier:
        if spec.operator in {'==', '==='} and '*' not in spec.version:
            pin = spec.version
    if pin is None:
        raise ValueError(f'No version pinned for {requirement.name}')
    for spec in requirement.specifier:
        if pin not in spec:
            raise ValueError(f'{requirement.name}: pinned version {pin} does not satisfy {spec}')
    return pin


def evaluate_marker(requirement: Requirement, extras: Iterable[str]) -> bool:
    """Evaluate whether `requirement` should be applied.

    This handles the special behaviour of ``extra`` in the marker spec, which
    is used in wheels to reference the extras being installed for the
    depending package (see PEP 508).
    """
    if requirement.marker is None:
        return True
    try:
        return requirement.marker.evaluate()
    except UndefinedEnvironmentName:
        extras = set(extras) or {''}
        for extra in extras:
            if requirement.marker.evaluate({'extra': extra}):
                return True
        return False


def get_dependencies(requirement: Requirement) -> Sequence[Requirement]:
    with tempfile.TemporaryDirectory() as cache_dir:
        # Pip uses a vendored version of packaging, so we have to translate
        req = PipRequirement(str(requirement))
        ireq = InstallRequirement(req, None)
        pypi = piptools.repositories.PyPIRepository([], cache_dir)
        # Map from InstallRequirement back to packaging Requirement
        deps = [Requirement(str(r.req)) for r in pypi.get_dependencies(ireq)]
        # Note: ireq.extras is normalised, unlike req.extras
        deps = [dep for dep in deps if evaluate_marker(dep, ireq.extras)]
        for dep in deps:
            dep.name = canonicalize_name(dep.name)
            # We've checked it, and 'extra' markers can cause problems later
            # as we don't have the context
            dep.marker = None
        return deps


def resolve(items: Iterable[Union[Package, str]]) -> Sequence[Union[Requirement, str]]:
    def add_constraint(pkg: Package):
        name = pkg.requirement.name
        if name in constraints:
            constraints[name] = merge_packages(constraints[name], pkg)
        else:
            constraints[name] = pkg
        return constraints[name]

    options = []
    constraints: Dict[str, Package] = {}
    install: Dict[str, Requirement] = {}
    q: Deque[Requirement] = deque()
    for item in items:
        if isinstance(item, str):
            options.append(item)
        elif item.constraint:
            add_constraint(item)
        else:
            q.append(item.requirement)

    errors = []
    while q:
        req = q.popleft()
        try:
            if req.marker and not req.marker.evaluate():
                continue      # Skip if marker doesn't apply
            if req.name in SKIP_PACKAGES:
                continue
            # Merge with any existing constraints
            req = add_constraint(Package(req)).requirement
            if req.url is None:
                version = version_from_requirement(req)
                # Remove any other specifiers, leaving just an exact version pin
                req = Requirement(str(req))  # Copy before mutating
                req.specifier = SpecifierSet(f'=={version}')
            # If it's already scheduled to be installed, with the same extras,
            # there is nothing more to be done.
            if req.name in install and install[req.name].extras == req.extras:
                continue
            install[req.name] = req
            q.extend(get_dependencies(req))
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        raise ResolutionError(errors)

    sorted_install = sorted(install.values(), key=lambda req: req.name)
    return options + sorted_install       # type: ignore


def collect_arguments(args: argparse.Namespace) -> Sequence[Union[Package, str]]:
    """Collect all requirements from command line."""
    reqs: List[Union[Package, str]] = []
    for requirements_file in args.requirement:
        reqs.extend(parse_requirements(requirements_file))
    for constraint_file in args.constraint:
        reqs.extend(parse_requirements(constraint_file, constraint=True))
    for default_file in args.default_versions:
        reqs.extend(parse_requirements(default_file, constraint=True, weak=True))
    reqs.extend(args.package)
    return reqs


def run_pip(args: List[str], dry_run: bool) -> None:
    if dry_run:
        print('pip {}'.format(' '.join(args)))
        if args != ['check']:
            print('Contents of {}:'.format(args[-1]))
            with open(args[-1]) as f:
                sys.stdout.write(f.read())
    else:
        ret = subprocess.call(['pip'] + args)
        if ret:
            sys.exit(ret)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--constraint', '-c', type=str, action='append', default=[],
        help='Constrain versions using the given constraints file')
    parser.add_argument(
        '--default-versions', '-d', type=str, action='append', default=[],
        help='Default constraints that can be overridden with pinned versions')
    parser.add_argument(
        '--requirement', '-r', type=str, action='append', default=[],
        help='Install from the given requirements file')
    parser.add_argument(
        '--dry-run', '-n', action='store_true',
        help='Just report what would be done')
    parser.add_argument(
        'package', type=parse_requirement, nargs='*',
        help='Extra requirements')
    args, extra_args = parser.parse_known_args()

    explicit_reqs = collect_arguments(args)
    try:
        reqs = resolve(explicit_reqs)
    except ResolutionError as exc:
        for error in exc.errors:
            print(error, file=sys.stderr)
        return 1

    with tempfile.NamedTemporaryFile('w', suffix='.txt') as req_file:
        for item in reqs:
            print(item, file=req_file)
        req_file.flush()
        run_pip(['install',
                 '--retries', '10', '--timeout', '30',
                 '--no-deps'] + extra_args + ['-r', req_file.name], args.dry_run)
    # Check that all dependencies were found
    run_pip(['check'], args.dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
