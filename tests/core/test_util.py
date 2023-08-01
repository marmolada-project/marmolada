from contextlib import nullcontext

import pytest

from marmolada.core import util


@pytest.mark.parametrize(
    "src_dicts, expected_result",
    (
        (
            ({1: 2, 2: 3}, {1: 4, 3: 5}),
            {1: 4, 2: 3, 3: 5},
        ),
        (
            ({1: {2: 3, 3: 4}}, {1: {3: 5, 4: 5}}),
            {1: {2: 3, 3: 5, 4: 5}},
        ),
        ((), ValueError),
        ((1, 2), TypeError),
        (
            ({1: {2: 3}}, {1: [3, 4]}),
            TypeError,
        ),
    ),
)
def test_merge_dicts(src_dicts, expected_result):
    if isinstance(expected_result, type) and issubclass(expected_result, Exception):
        expectation = pytest.raises(expected_result)
        succeeds = False
    else:
        expectation = nullcontext()
        succeeds = True

    with expectation:
        result = util.merge_dicts(*src_dicts)

    if succeeds:
        assert result == expected_result


@pytest.mark.parametrize(
    "camelcase, expected",
    (
        ("ABC", "abc"),
        ("ALongAndWindyRoad", "a_long_and_windy_road"),
        ("hahaHello", "haha_hello"),
        ("URLProcrastinator", "url_procrastinator"),
        ("AB", "ab"),
        ("", ""),
        ("X", "x"),
    ),
)
def test_camel_case_to_lower_with_underscores(camelcase, expected):
    assert util.camel_case_to_lower_with_underscores(camelcase) == expected
