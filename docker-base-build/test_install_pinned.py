import io
from typing import List, Union, Iterable

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
import pytest

import install_pinned
from install_pinned import Package


def test_package_repr() -> None:
    pkg = Package(Requirement('foo==0.1'))
    assert repr(pkg) == "Package('foo==0.1', constraint=False, weak=False)"
    pkg = Package('foo==0.1', constraint=True, weak=True)
    assert repr(pkg) == "Package('foo==0.1', constraint=True, weak=True)"


def test_requirement_eq() -> None:
    assert Package('foo[extra1,extra2] >=0.1, ==0.2') == Package('foo[extra2,extra1] ==0.2, >=0.1')
    assert not (Package('foo >=0.1, ==0.2') != Package('foo ==0.2, >=0.1'))
    assert Package('foo >=0.1') != Package('foo ==0.1')
    assert Package('foo >=0.1') != Package('bar >=0.1')
    assert Package('foo [test]') != Package('foo [bar]')
    assert Package('foo@ http://example.invalid') != Package('foo')
    assert Package('foo; python_version < "2.7"') != Package('foo; python_version > "2.7"')
    assert Package('foo', constraint=True) != Package('foo', constraint=False)
    assert Package('foo', weak=True) != Package('foo', weak=False)


@pytest.mark.parametrize(
    'specifiers, result',
    [
        ('==0.1', True),
        ('===0.1', True),
        ('>=0.1, <=0.1', False),    # Only one choice, but we're looking for ==
        ('>=0.1, ==0.1', True),
        ('==2.8.*', False)
    ]
)
def test_has_exact(specifiers: str, result: bool) -> None:
    assert install_pinned.has_exact(SpecifierSet(specifiers)) == result


def test_parse_requirement_req() -> None:
    req = install_pinned.parse_requirement('requests[security]>=2.8.1')
    assert isinstance(req, install_pinned.Package)
    assert req == Package('requests[security]>=2.8.1', constraint=False, weak=False)


def test_parse_requirement_option() -> None:
    req = install_pinned.parse_requirement('--no-binary pycuda')
    assert req == '--no-binary pycuda'


def test_parse_requirement_other() -> None:
    with pytest.warns(UserWarning, match='Requirement foo=1 could not be parsed'):
        req = install_pinned.parse_requirement('foo=1')
    assert req == 'foo=1'


@pytest.mark.parametrize(
    'constraint, weak',
    [(False, False), (True, False), (True, True)]
)
def test_parse_requirements_simple(tmp_path, constraint: bool, weak: bool) -> None:
    filename = tmp_path / 'requirements.txt'
    filename.write_text('''
# A comment
foo==0.1        # An end-of-line comment

--an-option
''')
    reqs = install_pinned.parse_requirements(str(filename), constraint=constraint, weak=weak)
    assert set(reqs) == {
        Package('foo==0.1', constraint=constraint, weak=weak),
        '--an-option'
    }


def test_parse_requirements_nested(tmp_path) -> None:
    filename = tmp_path / 'base.txt'
    (tmp_path / 'requirements.txt').write_text('required>=1.0\n')
    (tmp_path / 'constraints.txt').write_text('constrained<=2.0\n')
    (tmp_path / 'defaults.txt').write_text('defaulted==1.5\n')
    filename.write_text(f'''
-d defaults.txt
-r requirements.txt
-c {tmp_path / "constraints.txt"}
''')
    reqs = install_pinned.parse_requirements(str(filename))
    assert set(reqs) == {
        Package('required>=1.0', constraint=False, weak=False),
        Package('constrained<=2.0', constraint=True, weak=False),
        Package('defaulted==1.5', constraint=True, weak=True)
    }


def test_parse_requirements_http(mocker) -> None:
    url1 = 'https://example.invalid/foo/requirements.txt'
    url2 = 'https://example.invalid/constraints.txt'
    content = {
        url1:
            b'-c ../constraints.txt\n'
            b'foo>=1.0\n',
        url2: b'bar==2.0\n'
    }

    def urlopen_replacement(url):
        return io.BytesIO(content[url])

    mocker.patch('urllib.request.urlopen', side_effect=urlopen_replacement)
    reqs = install_pinned.parse_requirements(url1)
    assert set(reqs) == {
        Package('foo>=1.0'),
        Package('bar==2.0', constraint=True)
    }


def test_merge_packages_simple() -> None:
    pkg = install_pinned.merge_packages(
        Package('requests [security,tests] >= 2.8.1, == 2.8.* ; python_version >= "2.7"'),
        Package('requests [security,foo] >= 2.7')
    )
    assert pkg == Package(
        'requests [security,foo,tests]>=2.7,>=2.8.1,==2.8.*; python_version >= "2.7"')


def test_merge_packages_constraint() -> None:
    req1 = Requirement('foo >= 2.8')
    req2 = Requirement('foo [test] < 3.0')
    pkg = install_pinned.merge_packages(
        Package(req1, constraint=True),
        Package(req2, constraint=True)
    )
    assert pkg == Package('foo [test] >=2.8, <3.0', constraint=True)

    pkg = install_pinned.merge_packages(
        Package(req1, constraint=False),
        Package(req2, constraint=True)
    )
    assert pkg == Package('foo [test] >=2.8, <3.0', constraint=False)


def test_merge_packages_markers() -> None:
    pkg = install_pinned.merge_packages(
        Package('foo >= 1.0 ; python_version >= "2.7"'),
        Package('foo < 1.0 ; python_version < "2.7"')
    )
    assert pkg == Package('foo >= 1.0 ; python_version >= "2.7"')

    # Check symmetry
    pkg = install_pinned.merge_packages(
        Package('foo < 1.0 ; python_version < "2.7"'),
        Package('foo >= 1.0 ; python_version >= "2.7"')
    )
    assert pkg == Package('foo >= 1.0 ; python_version >= "2.7"')


def test_merge_packages_url_and_specifier() -> None:
    pkg = install_pinned.merge_packages(
        Package('foo[bar] >= 2.0'),
        Package('foo @ https://invalid.com')
    )
    assert pkg == Package('foo[bar] @ https://invalid.com')

    with pytest.raises(ValueError, match='Cannot combine URL .* with specifier ==2.0'):
        install_pinned.merge_packages(
            Package('foo[bar] == 2.0'),
            Package('foo @ https://invalid.com')
        )


def test_merge_packages_override_default() -> None:
    pkg = install_pinned.merge_packages(
        Package('foo == 2.0', weak=True),
        Package('foo[test] == 2.1')
    )
    assert pkg == Package('foo[test] == 2.1')

    # Only exact versions override defaults
    pkg = install_pinned.merge_packages(
        Package('foo == 2.0', weak=True),
        Package('foo[test] >= 1.0')
    )
    assert pkg == Package('foo[test] >=1.0, ==2.0')


def test_merge_packages_mixed_names() -> None:
    with pytest.raises(ValueError, match='different names'):
        install_pinned.merge_packages(Package('foo==0.1'), Package('bar==0.2'))


def test_merge_packages_mixed_urls() -> None:
    with pytest.raises(ValueError, match='inconsistent URLs'):
        install_pinned.merge_packages(Package('foo @ http://url1'), Package('foo @ http://url2'))


@pytest.mark.parametrize(
    'requirement',
    ['foo == 1.2', 'foo >= 1.0, < 2.0, == 1.2']
)
def test_version_from_requirement(requirement: str) -> None:
    assert install_pinned.version_from_requirement(Requirement(requirement)) == '1.2'


@pytest.mark.parametrize(
    'requirement',
    ['foo', 'foo >= 1.2', 'foo == 1.2.*']
)
def test_version_from_requirement_missing(requirement: str) -> None:
    with pytest.raises(ValueError, match='No version pinned'):
        install_pinned.version_from_requirement(Requirement(requirement))


def test_version_from_requirement_url() -> None:
    with pytest.raises(ValueError, match='from an URL'):
        install_pinned.version_from_requirement(
            Requirement('foo @ git+https://invalid.example/foo'))


def test_version_from_requirement_inconsistent() -> None:
    with pytest.raises(ValueError, match='does not satisfy'):
        install_pinned.version_from_requirement(Requirement('foo == 1.2, >= 2.0'))


@pytest.mark.parametrize(
    'requirement, extras, result',
    [
        ('foo', set(), True),
        ('foo; python_version >= "2.7"', set(), True),
        ('foo; extra == "test"', set(), False),
        ('foo; extra == "test"', {'other'}, False),
        ('foo; extra == "test"', {'test', 'other'}, True)
    ]
)
def test_evaluate_marker(requirement: str, extras: Iterable[str], result: bool) -> None:
    assert install_pinned.evaluate_marker(Requirement(requirement), extras) == result


@pytest.mark.internet
def test_get_dependencies() -> None:
    reqs = install_pinned.get_dependencies(Requirement('dask[array] == 2021.2.0'))
    # Wrap into Package just to use its __eq__ and __hash__
    pkgs = set(Package(req) for req in reqs)
    assert pkgs == {
        Package('pyyaml'),
        Package('numpy>=1.15.1'),
        Package('toolz>=0.8.2')
    }


@pytest.mark.internet
def test_resolve() -> None:
    items: List[Union[Package, str]] = [
        Package('katsdptelstate == 0.10'),
        Package('redis == 3.5.3', constraint=True),
        Package('msgpack == 1.0.1', constraint=True),
        Package('six == 1.15.0', constraint=True),
        Package('netifaces == 0.10.9', constraint=True),
        Package('numpy == 1.20.1', constraint=True),
        Package('pycuda == 2020.0', constraint=True),   # Not required so shouldn't be included
        Package('numpy == 1.17.1', constraint=True, weak=True),   # Should be overridden
        '--no-binary pycuda'       # Just to test options
    ]
    reqs = install_pinned.resolve(items)
    # Convert Requirement to Package just to use __eq__/__hash__
    pkgs = set(Package(req) if isinstance(req, Requirement) else req for req in reqs)
    assert pkgs == {
        Package('katsdptelstate == 0.10'),
        Package('redis == 3.5.3'),
        Package('msgpack == 1.0.1'),
        Package('six == 1.15.0'),
        Package('netifaces == 0.10.9'),
        Package('numpy == 1.20.1'),
        '--no-binary pycuda'
    }


@pytest.mark.internet
def test_resolve_fail() -> None:
    items: List[Union[Package, str]] = [
        Package('katsdptelstate == 0.10'),
        Package('redis == 3.5.3', constraint=True),
        Package('msgpack == 1.0.1', constraint=True),
        Package('six == 1.15.0', constraint=True),
    ]
    with pytest.raises(install_pinned.ResolutionError) as exc_info:
        install_pinned.resolve(items)
    assert set(exc_info.value.errors) == {
        'No version pinned for netifaces',
        'No version pinned for numpy'
    }
