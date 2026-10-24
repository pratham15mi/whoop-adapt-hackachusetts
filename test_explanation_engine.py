"""Test cases for the explanation engine.

The four canonical scenarios from the spec are the primary tests; a few extra
cases lock in the boundary behaviour and input validation.
"""

import json

import pytest

from explanation_engine import Action, explain


# --- The four canonical scenarios --------------------------------------------

def test_scenario_1_healthy():
    d = explain(recovery_percent=75, sleep_hours=8)
    assert d.action is Action.NO_CHANGE
    assert d.explanation == (
        "No changes needed. Your recovery and sleep support your current plan."
    )


def test_scenario_2_moderate():
    d = explain(recovery_percent=55, sleep_hours=6)
    assert d.action is Action.SHORTEN_OPTIONAL_WORKOUT
    assert d.explanation == (
        "Shortening your optional workout by 30 min to protect recovery."
    )


def test_scenario_3_critical():
    d = explain(recovery_percent=30, sleep_hours=4.5)
    assert d.action is Action.PROTECT_SLEEP_WINDOW
    assert d.explanation == (
        "Protecting your 8-hour sleep window tonight \u2014 moving admin "
        "tasks to a free slot tomorrow."
    )


def test_scenario_4_exam():
    d = explain(recovery_percent=35, sleep_hours=5, exam=True)
    assert d.action is Action.PROTECT_TOMORROW
    assert d.explanation == (
        "Protect Tomorrow activated: reshuffling your schedule to secure "
        "sleep before your exam."
    )


# --- Behavioural edge cases --------------------------------------------------

def test_exam_flag_ignored_when_fully_recovered():
    # An exam tomorrow but healthy numbers -> nothing to protect against.
    d = explain(recovery_percent=80, sleep_hours=8, exam=True)
    assert d.action is Action.NO_CHANGE


def test_exam_overrides_critical():
    # Critical numbers + exam -> Protect Tomorrow wins over sleep-window.
    d = explain(recovery_percent=30, sleep_hours=4.5, exam=True)
    assert d.action is Action.PROTECT_TOMORROW


def test_low_recovery_alone_triggers_workout_trim():
    d = explain(recovery_percent=58, sleep_hours=8)
    assert d.action is Action.SHORTEN_OPTIONAL_WORKOUT


def test_short_sleep_alone_triggers_workout_trim():
    d = explain(recovery_percent=75, sleep_hours=6.5)
    assert d.action is Action.SHORTEN_OPTIONAL_WORKOUT


# --- JSON serialization ------------------------------------------------------

def test_to_dict_shape_and_types():
    d = explain(recovery_percent=55, sleep_hours=6)
    payload = d.to_dict()
    assert payload == {
        "action": "shorten_optional_workout",  # plain string, not Enum
        "explanation": (
            "Shortening your optional workout by 30 min to protect recovery."
        ),
        "recovery_percent": 55,
        "sleep_hours": 6,
        "exam": False,
    }
    # The whole payload must be JSON-serializable for Bailey's UI.
    assert json.loads(json.dumps(payload)) == payload


@pytest.mark.parametrize("recovery", [-1, 101])
def test_invalid_recovery_rejected(recovery):
    with pytest.raises(ValueError):
        explain(recovery_percent=recovery, sleep_hours=8)


@pytest.mark.parametrize("sleep", [-1, 25])
def test_invalid_sleep_rejected(sleep):
    with pytest.raises(ValueError):
        explain(recovery_percent=75, sleep_hours=sleep)
