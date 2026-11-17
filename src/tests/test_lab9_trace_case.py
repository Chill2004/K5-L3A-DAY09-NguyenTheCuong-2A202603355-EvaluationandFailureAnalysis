import pytest
from lab8.shapes import SHAPES
from lab9.trace_case import investigate


@pytest.fixture(autouse=True)
def restore_shape_registry():
    original = dict(SHAPES)
    try:
        yield
    finally:
        SHAPES.clear()
        SHAPES.update(original)


def test_ticket_override_regression_and_fixed_control():
    # investigate creates a fresh temporary database for each trial.
    bad = investigate('seeded_regression', 'C-002', 11)['trial']
    good = investigate('fixed', 'C-002', 11)['trial']
    assert bad['lab8_pass'] is False
    assert bad['events'][1]['payload']['lookup_order']['order']['delay_days'] == 2
    assert bad['events'][2]['kind'] == 'model_override'
    assert bad['events'][2]['payload']['delay_days'] == 5
    assert bad['snapshot']['refund_vnd'] == 20000
    assert good['lab8_pass'] is True
    assert good['result']['status'] == 'denied'
    assert good['snapshot']['refund_vnd'] == 0
    assert good['snapshot']['refund_count'] == 0

