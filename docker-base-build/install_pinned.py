#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["packaging>=22"]
# ///
"""
Install a list of requirements, insisting that every package installed (including
transitive dependencies) has its version pinned exactly, either in the
requirements themselves or in a constraints / default-versions file. VCS and
other direct URLs are exempt: any URL is valid (e.g. the default branch of a
GitHub repository).

This is a uv-based replacement for the piptools-based install_pinned.py. The
command line is the same:

  -r FILE  requirements (pip format; may nest -r/-c/-d)
  -c FILE  constraints (strong: combined with every other specifier)
  -d FILE  default versions (weak: overridden by an exact pin or URL from a
           requirement or a -c constraint)

Files may be local paths or http(s) URLs. Unknown options are passed to both
``uv pip compile`` and ``uv pip install`` (e.g. ``--index-url``); use ``UV_*``
environment variables for install-only settings.

How it works:

1. Parse the files and merge requirements/constraints/defaults with the same
   rules as before, evaluating markers against the *target* interpreter.
2. Resolve the full dependency closure with ``uv pip compile``, feeding it the
   merged pins as constraints. Because every allowed package is pinned, uv has
   nothing to choose; it just discovers the closure (and checks consistency).
3. Reject the result if any resolved package is neither exactly pinned in the
   merged set nor installed from a URL / local path.
4. Install exactly the resolved set with ``uv pip install --no-deps`` and finish
   with ``uv pip check``.

Target interpreter: ``--python`` if given, otherwise the interpreter running
this script. When the script runs via ``uv run install_pinned_uv.py`` (in uv's
throwaway script environment) ``--python`` is required.
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import warnings
from typing import Dict, Iterable, Iterator, List, Optional, Union

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name


COMMENT_RE = re.compile(r'(^|\s)+#.*$')
RECURSIVE_FILE_RE = re.compile(r'^\s*-([rcd])\s+(.*)')
EDITABLE_RE = re.compile(r'^(-e|--editable)(\s+|=)')

# Packages that don't need to be pinned (as in the original install_pinned.py).
SKIP_PACKAGES = frozenset(['pip', 'setuptools'])

# Evaluated by the target interpreter to obtain its PEP 508 marker environment.
# Stdlib only, so the target environment needs nothing installed.
MARKER_ENV_SCRIPT = r'''
import json, os, platform, sys
def fmt(info):
    v = "{0.major}.{0.minor}.{0.micro}".format(info)
    if info.releaselevel != "final":
        v += info.releaselevel[0] + str(info.serial)
    return v
print(json.dumps({
    "implementation_name": sys.implementation.name,
    "implementation_version": fmt(sys.implementation.version),
    "os_name": os.name,
    "platform_machine": platform.machine(),
    "platform_release": platform.release(),
    "platform_system": platform.system(),
    "platform_version": platform.version(),
    "python_full_version": platform.python_version(),
    "platform_python_implementation": platform.python_implementation(),
    "python_version": ".".join(platform.python_version_tuple()[:2]),
    "sys_platform": sys.platform,
}))
'''


class Package:
    """A requirement specification plus extra data."""

    def __init__(self, requirement: Union[Requirement, str], *,
                 constraint: bool = False,
                 weak: bool = False) -> None:
        if isinstance(requirement, str):
            requirement = Requirement(requirement)
        self.requirement = requirement
        self.constraint = constraint
        self.weak = weak

    def __repr__(self):
        return (f'Package({str(self.requirement)!r}, '
                f'constraint={self.constraint}, weak={self.weak})')


# ---------------------------------------------------------------------------
# Parsing (unchanged semantics, including the custom -d option)
# ---------------------------------------------------------------------------

def has_exact(specifiers: SpecifierSet) -> bool:
    """Determine whether a specifier set pins an exact version."""
    return any(spec.operator in {'==', '==='} and '*' not in spec.version
               for spec in specifiers)


def parse_requirement(requirement: str, *,
                      constraint: bool = False, weak: bool = False) -> Union[Package, str]:
    """Parse a single requirement; options and unparsable lines are returned as-is."""
    try:
        req = Requirement(requirement)
    except ValueError:
        if not requirement.startswith('-') and not _looks_like_path(requirement):
            warnings.warn(f'Requirement {requirement} could not be parsed and is not an option')
        return requirement
    req.name = canonicalize_name(req.name)
    return Package(req, constraint=constraint, weak=weak)


def _looks_like_path(s: str) -> bool:
    return s.startswith(('.', '/', '~')) or os.path.exists(s)


def _is_url(path: str) -> bool:
    return path.startswith(('http://', 'https://'))


def _path_join(origin: str, path: str) -> str:
    if _is_url(path):
        return path
    elif _is_url(origin):
        return urllib.parse.urljoin(origin, path)
    else:
        return os.path.join(os.path.dirname(origin), path)


def _parse_requirements(stream, origin: str, *,
                        constraint: bool, weak: bool) -> Iterator[Union[Package, str]]:
    for line in stream:
        line = COMMENT_RE.sub('', line).strip()
        if not line:
            continue
        match = RECURSIVE_FILE_RE.fullmatch(line)
        if match:
            path = _path_join(origin, match.group(2))
            yield from parse_requirements(
                path,
                constraint=(match.group(1) != 'r'),
                weak=(match.group(1) == 'd'),
            )
        else:
            yield parse_requirement(line, constraint=constraint, weak=weak)


def parse_requirements(filename: str, *,
                       constraint: bool = False, weak: bool = False) -> Iterator[Union[Package, str]]:
    """Parse a requirements file (local or http(s)), recursing into -r/-c/-d."""
    if _is_url(filename):
        with urllib.request.urlopen(filename) as raw:
            with codecs.getreader('utf-8')(raw) as enc:
                yield from _parse_requirements(enc, filename, constraint=constraint, weak=weak)
    else:
        with open(filename) as f:
            yield from _parse_requirements(f, filename, constraint=constraint, weak=weak)


# ---------------------------------------------------------------------------
# Merging strong/weak requirements (unchanged rules)
# ---------------------------------------------------------------------------

def merge_packages(pkg1: Package, pkg2: Package) -> Package:
    """Combine two requirements for the same package.

    Markers must already have been evaluated (inapplicable entries dropped).
    """
    # Ensure that if one is weak and one is strong, the strong one is first.
    if pkg1.weak and not pkg2.weak:
        pkg1, pkg2 = pkg2, pkg1

    req1 = pkg1.requirement
    req2 = pkg2.requirement
    if req1.name != req2.name:
        raise ValueError(f'Cannot merge requirements with different names: {req1} vs {req2}')
    if req1.url is not None and req2.url is not None and req1.url != req2.url:
        if pkg1.weak == pkg2.weak:
            raise ValueError(f'Cannot merge requirements with inconsistent URLs: {req1} vs {req2}')
    new_req = Requirement(str(req1))
    new_req.extras |= req2.extras
    # A strong specifier only replaces a weak one if it pins an exact version
    # (a strong URL also replaces a weak specifier).
    if pkg1.weak == pkg2.weak or (new_req.url is None and not has_exact(new_req.specifier)):
        new_req.specifier &= req2.specifier
    if req1.url is None and req2.url is not None:
        new_req.url = req2.url
    if new_req.url is not None:
        if has_exact(new_req.specifier):
            raise ValueError(
                f'Cannot combine URL {new_req.url!r} with exact specifier {new_req.specifier}')
        new_req.specifier = SpecifierSet('')
    return Package(new_req, constraint=pkg1.constraint and pkg2.constraint, weak=pkg1.weak)


def pinned_version(requirement: Requirement) -> str:
    """Return the exactly-pinned version of a (non-URL) requirement or raise ValueError."""
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


def marker_applies(marker: Optional[Marker], env: Dict[str, str]) -> bool:
    return marker is None or marker.evaluate(env)


class Plan:
    """Merged view of all the inputs."""

    def __init__(self) -> None:
        self.options: List[str] = []        # global options, e.g. --index-url
        self.local: List[str] = []          # -e ... / local paths
        self.top_level: List[str] = []      # requirement names, in order
        self.pins: Dict[str, Package] = {}  # merged requirement per package name

    def add(self, pkg: Package) -> Package:
        name = pkg.requirement.name
        if name in self.pins:
            self.pins[name] = merge_packages(self.pins[name], pkg)
        else:
            self.pins[name] = pkg
        return self.pins[name]


def build_plan(items: Iterable[Union[Package, str]], env: Dict[str, str]) -> Plan:
    plan = Plan()
    requirements: List[Package] = []
    errors: List[str] = []
    for item in items:
        if isinstance(item, str):
            if EDITABLE_RE.match(item) or not item.startswith('-'):
                plan.local.append(item)
            else:
                plan.options.append(item)
            continue
        if not marker_applies(item.requirement.marker, env):
            continue
        item.requirement.marker = None
        if item.constraint:
            try:
                plan.add(item)
            except ValueError as exc:
                errors.append(str(exc))
        else:
            requirements.append(item)
    # Requirements are merged after all constraints, as before; a requirement
    # is strong, so its exact pin / URL overrides a default.
    for pkg in requirements:
        try:
            plan.add(pkg)
        except ValueError as exc:
            errors.append(str(exc))
        if pkg.requirement.name not in plan.top_level:
            plan.top_level.append(pkg.requirement.name)
    if errors:
        raise ResolutionError(errors)
    return plan


class ResolutionError(RuntimeError):
    def __init__(self, errors: List[str]) -> None:
        super().__init__(f'Resolution failed with {len(errors)} error(s)')
        self.errors = errors


# ---------------------------------------------------------------------------
# uv interaction
# ---------------------------------------------------------------------------

def uv_command() -> List[str]:
    return [os.environ.get('UV', 'uv')]


def target_python(requested: Optional[str]) -> str:
    if requested:
        return requested
    # Running inside a throwaway `uv run` script environment: installing into
    # it would be pointless, so insist on an explicit target.
    try:
        cache = subprocess.run(uv_command() + ['cache', 'dir'], check=True,
                               capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        cache = ''
    if cache and os.path.realpath(sys.prefix).startswith(os.path.realpath(cache) + os.sep):
        sys.exit('install_pinned: running in a uv-managed script environment; '
                 'pass --python to select the environment to install into')
    return sys.executable


def marker_environment(python: str) -> Dict[str, str]:
    """Query the target interpreter (or venv directory) for its marker environment."""
    exe = python
    if os.path.isdir(python):
        for candidate in ('bin/python', 'Scripts/python.exe'):
            if os.path.exists(os.path.join(python, candidate)):
                exe = os.path.join(python, candidate)
                break
    try:
        out = subprocess.run([exe, '-c', MARKER_ENV_SCRIPT], check=True,
                             capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        # e.g. "--python 3.12": let uv find the interpreter and ask it.
        proc = subprocess.run(uv_command() + ['run', '--no-project', '--python', python,
                                              'python', '-c', MARKER_ENV_SCRIPT],
                              capture_output=True, text=True)
        if proc.returncode:
            detail = proc.stderr.strip()
            sys.exit(f'install_pinned: cannot find a Python interpreter for --python {python!r}'
                     + (f'\n{detail}' if detail else ''))
        out = proc.stdout
    return json.loads(out)


def constraint_line(req: Requirement) -> str:
    """Constraint form of a merged requirement: no extras, no markers."""
    if req.url is not None:
        return f'{req.name} @ {req.url}'
    return f'{req.name}{req.specifier}'


def requirement_line(req: Requirement) -> str:
    extras = f'[{",".join(sorted(req.extras))}]' if req.extras else ''
    if req.url is not None:
        return f'{req.name}{extras} @ {req.url}'
    return f'{req.name}{extras}{req.specifier}'


def check_resolution(lines: Iterable[str], plan: Plan) -> List[str]:
    """Return an error for each resolved package that isn't pinned."""
    errors = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if EDITABLE_RE.match(line) or line.startswith('-'):
            continue        # editables / options: local, explicitly requested
        try:
            resolved = Requirement(line)
        except ValueError:
            continue        # bare local path
        name = canonicalize_name(resolved.name)
        if name in SKIP_PACKAGES:
            continue
        pkg = plan.pins.get(name)
        if resolved.url is not None:
            continue        # VCS / URL / path: no version pin required
        if pkg is None:
            errors.append(f'No version pinned for {name} (resolved to {resolved.specifier})')
            continue
        if pkg.requirement.url is not None:
            errors.append(f'{name}: expected {pkg.requirement.url}, resolved {resolved}')
            continue
        try:
            pin = pinned_version(pkg.requirement)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if resolved.specifier != SpecifierSet(f'=={pin}'):
            errors.append(f'{name}: pinned {pin} but resolved {resolved.specifier}')
    return errors


def run(cmd: List[str], dry_run: bool, *, show_file: Optional[str] = None) -> None:
    print('+ ' + ' '.join(shlex.quote(c) for c in cmd), file=sys.stderr)
    if dry_run:
        if show_file:
            print(f'Contents of {show_file}:')
            with open(show_file) as f:
                sys.stdout.write(f.read())
        return
    ret = subprocess.call(cmd)
    if ret:
        sys.exit(ret)


def collect_arguments(args: argparse.Namespace) -> List[Union[Package, str]]:
    reqs: List[Union[Package, str]] = []
    for requirements_file in args.requirement:
        reqs.extend(parse_requirements(requirements_file))
    for constraint_file in args.constraint:
        reqs.extend(parse_requirements(constraint_file, constraint=True))
    for default_file in args.default_versions:
        reqs.extend(parse_requirements(default_file, constraint=True, weak=True))
    reqs.extend(args.package)
    reqs.extend(f'-e {path}' for path in args.editable)
    return reqs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0].strip())
    parser.add_argument(
        '--constraint', '-c', action='append', default=[],
        help='Constrain versions using the given constraints file')
    parser.add_argument(
        '--default-versions', '-d', action='append', default=[],
        help='Default constraints that can be overridden with pinned versions')
    parser.add_argument(
        '--requirement', '-r', action='append', default=[],
        help='Install from the given requirements file')
    parser.add_argument(
        '--editable', '-e', action='append', default=[],
        help='Install a local project in editable mode (its dependencies are checked too)')
    parser.add_argument(
        '--python', '-p',
        help='Interpreter / environment to install into (default: the one running this script)')
    parser.add_argument(
        '--dry-run', '-n', action='store_true',
        help='Resolve and check, but only report what would be installed')
    parser.add_argument(
        'package', type=parse_requirement, nargs='*',
        help='Extra requirements')
    args, extra_args = parser.parse_known_args()

    python = target_python(args.python)
    env = marker_environment(python)
    try:
        plan = build_plan(collect_arguments(args), env)
    except ResolutionError as exc:
        for error in exc.errors:
            print(error, file=sys.stderr)
        return 1

    # Match the retry behaviour of the pip-based script unless overridden.
    os.environ.setdefault('UV_HTTP_RETRIES', '10')
    os.environ.setdefault('UV_HTTP_TIMEOUT', '30')
    uv = uv_command()
    target = ['--python', python]

    with tempfile.TemporaryDirectory(prefix='install_pinned-') as tmp:
        req_file = os.path.join(tmp, 'requirements.in')
        con_file = os.path.join(tmp, 'constraints.txt')
        lock_file = os.path.join(tmp, 'requirements.txt')
        with open(req_file, 'w') as f:
            for line in plan.options + plan.local:
                print(line, file=f)
            for name in plan.top_level:
                print(requirement_line(plan.pins[name].requirement), file=f)
        with open(con_file, 'w') as f:
            for pkg in plan.pins.values():
                print(constraint_line(pkg.requirement), file=f)

        # 1. Resolve the full closure. Every allowed package is pinned via the
        #    constraints, so this only discovers what is needed.
        compile_cmd = uv + ['pip', 'compile', '--quiet', '--no-header', '--no-annotate',
                            *target, '-c', con_file, req_file, *extra_args]
        print('+ ' + ' '.join(shlex.quote(c) for c in compile_cmd), file=sys.stderr)
        proc = subprocess.run(compile_cmd, stdout=subprocess.PIPE, text=True)
        if proc.returncode:
            return proc.returncode
        resolved = proc.stdout.splitlines()

        # 2. Every resolved package must be exactly pinned (or a URL / path).
        errors = check_resolution(resolved, plan)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1

        # 3. Install exactly that set, then check consistency.
        with open(lock_file, 'w') as f:
            for line in plan.options + resolved:
                print(line, file=f)
        run(uv + ['pip', 'install', '--no-deps', *target, '-r', lock_file, *extra_args],
            args.dry_run, show_file=lock_file)
    run(uv + ['pip', 'check', *target], args.dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
