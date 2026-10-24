"""
Explanation Engine
==================

The glue between the recovery number (Gui) and the calendar UI (Bailey).

Takes a recovery percentage and last night's sleep hours (plus an optional
"exam tomorrow" flag) and returns a structured decision: *what* to change to
the user's plan and *why*, in plain language the calendar UI can display
directly.

Usage (library):
    from explanation_engine import explain
    result = explain(recovery_percent=55, sleep_hours=6)
    print(result.explanation)

Usage (CLI):
    python explanation_engine.py 55 6
    python explanation_engine.py 35 5 --exam
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Action(str, Enum):
    """Machine-readable action the calendar UI should take."""

    NO_CHANGE = "no_change"
    SHORTEN_OPTIONAL_WORKOUT = "shorten_optional_workout"
    PROTECT_SLEEP_WINDOW = "protect_sleep_window"
    PROTECT_TOMORROW = "protect_tomorrow"


@dataclass
class Decision:
    """The engine's output.

    Attributes:
        action:        Machine-readable action for the calendar UI to execute.
        explanation:   Plain-text sentence describing what changes and why.
        recovery_percent / sleep_hours / exam: Echo of the inputs, so the UI
            can log or display the reasoning context.
    """

    action: Action
    explanation: str
    recovery_percent: float
    sleep_hours: float
    exam: bool = False

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.explanation

    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON output / API responses.

        ``action`` is emitted as its string value (not the Enum) so the
        payload is directly JSON-serializable and stable for Bailey's UI to
        switch on.
        """
        return {
            "action": self.action.value,
            "explanation": self.explanation,
            "recovery_percent": self.recovery_percent,
            "sleep_hours": self.sleep_hours,
            "exam": self.exam,
        }


# --- Tunable thresholds -------------------------------------------------------
# Kept as module-level constants so they're easy to tweak as Gui's recovery
# model and the team's calendar heuristics evolve.

TARGET_SLEEP_HOURS = 8.0          # the sleep window we try to protect
LOW_RECOVERY = 60.0               # below this, start protecting recovery
CRITICAL_RECOVERY = 40.0          # below this, protect the full sleep window
SHORT_SLEEP = 7.0                 # sleep below this is a contributing stressor
CRITICAL_SLEEP = 5.5              # sleep below this is a serious deficit


def _validate(recovery_percent: float, sleep_hours: float) -> None:
    if not 0 <= recovery_percent <= 100:
        raise ValueError(
            f"recovery_percent must be between 0 and 100, got {recovery_percent}"
        )
    if not 0 <= sleep_hours <= 24:
        raise ValueError(
            f"sleep_hours must be between 0 and 24, got {sleep_hours}"
        )


def explain(
    recovery_percent: float,
    sleep_hours: float,
    exam: bool = False,
) -> Decision:
    """Turn a recovery reading into a plan change + plain-language reason.

    The logic is an escalating ladder. It is evaluated most-severe-first so
    the strongest justified intervention wins:

        1. Exam tomorrow + strained recovery  -> Protect Tomorrow
        2. Critically low recovery / sleep     -> Protect the sleep window
        3. Moderately low recovery / sleep     -> Trim the optional workout
        4. Everything healthy                  -> No change
    """
    _validate(recovery_percent, sleep_hours)

    strained = recovery_percent < LOW_RECOVERY or sleep_hours < SHORT_SLEEP
    critical = (
        recovery_percent < CRITICAL_RECOVERY or sleep_hours < CRITICAL_SLEEP
    )

    # 1. Exam flag is the highest-priority override, as long as there's any
    #    recovery/sleep strain worth protecting against.
    if exam and strained:
        return Decision(
            action=Action.PROTECT_TOMORROW,
            explanation=(
                "Protect Tomorrow activated: reshuffling your schedule to "
                "secure sleep before your exam."
            ),
            recovery_percent=recovery_percent,
            sleep_hours=sleep_hours,
            exam=exam,
        )

    # 2. Critically low recovery or sleep -> protect the full sleep window and
    #    push non-essential tasks out to a free slot tomorrow.
    if critical:
        return Decision(
            action=Action.PROTECT_SLEEP_WINDOW,
            explanation=(
                f"Protecting your {int(TARGET_SLEEP_HOURS)}-hour sleep window "
                "tonight \u2014 moving admin tasks to a free slot tomorrow."
            ),
            recovery_percent=recovery_percent,
            sleep_hours=sleep_hours,
            exam=exam,
        )

    # 3. Moderately low recovery or short sleep -> trim the optional workout.
    if strained:
        return Decision(
            action=Action.SHORTEN_OPTIONAL_WORKOUT,
            explanation=(
                "Shortening your optional workout by 30 min to protect "
                "recovery."
            ),
            recovery_percent=recovery_percent,
            sleep_hours=sleep_hours,
            exam=exam,
        )

    # 4. Healthy recovery and sleep -> leave the plan alone.
    return Decision(
        action=Action.NO_CHANGE,
        explanation=(
            "No changes needed. Your recovery and sleep support your current "
            "plan."
        ),
        recovery_percent=recovery_percent,
        sleep_hours=sleep_hours,
        exam=exam,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recovery explanation engine: turns recovery %% + sleep hours "
            "into a plan change and a plain-language reason."
        )
    )
    parser.add_argument(
        "recovery_percent",
        type=float,
        help="Recovery percentage (0-100), e.g. 55",
    )
    parser.add_argument(
        "sleep_hours",
        type=float,
        help="Hours slept last night (0-24), e.g. 6",
    )
    parser.add_argument(
        "--exam",
        action="store_true",
        help="Flag that the user has an exam tomorrow.",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the decision as a structured JSON object instead of text.",
    )
    return parser


def main(argv: List[str] | None = None) -> None:  # pragma: no cover
    args = _build_arg_parser().parse_args(argv)
    decision = explain(
        recovery_percent=args.recovery_percent,
        sleep_hours=args.sleep_hours,
        exam=args.exam,
    )
    if args.as_json:
        print(json.dumps(decision.to_dict(), indent=2))
    else:
        print(f"action      : {decision.action.value}")
        print(f"explanation : {decision.explanation}")


if __name__ == "__main__":  # pragma: no cover
    main()
