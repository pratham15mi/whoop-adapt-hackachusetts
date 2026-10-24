# WHOOP Adapt — Hackachusetts

An adaptive scheduling demo that turns a **recovery %** and **sleep hours** reading
into a concrete plan change plus a plain-language explanation — the glue between
the recovery number and a calendar UI.

## Contents

| File | What it is |
|------|------------|
| `whoop-adapt.html` | Self-contained 3-screen demo web app. No server, no backend, no network calls — open it directly in any browser. |
| `explanation_engine.py` | Standalone Python engine (library + CLI + optional HTTP server) implementing the same decision logic. |
| `test_explanation_engine.py` | Pytest suite — the 4 canonical scenarios plus edge cases (13 tests). |

## The demo app (`whoop-adapt.html`)

Dark, mobile-sized, WHOOP-style UI with three screens:

1. **Your Day** — today's date, an editable recovery card (Recovery % + Sleep h),
   and the day's calendar events tagged **Fixed** 🔒 or **Flexible** ↕.
2. **Protect Tomorrow** — mark an important event, set travel/routine/sleep-goal
   inputs and an exam-flag toggle, then **Build proposed plan**.
3. **Review your plan** — suggested changes as cards (Fixed = locked, Flexible =
   moved/shortened), with **Approve changes** / **Edit proposal**.

Change the Recovery/Sleep inputs or the exam toggle and rebuild — screen 3 updates
live. Just open the file in a browser; everything runs client-side.

## Decision logic

`explainDecision(recoveryPercent, sleepHours, examFlag) → { action, explanation }`

| Condition | Action |
|-----------|--------|
| `examFlag` **and** (`recovery < 60` **or** `sleep < 7`) | `protect_tomorrow` |
| `recovery < 40` **or** `sleep < 5.5` | `protect_sleep_window` |
| `recovery < 60` **or** `sleep < 7` | `shorten_optional_workout` |
| otherwise | `no_change` |

The JS in `whoop-adapt.html` and the Python in `explanation_engine.py` use
identical thresholds and explanation strings.

## Verified scenarios

| Recovery | Sleep | Exam | Expected action |
|----------|-------|------|-----------------|
| 75% | 8h   | no  | `no_change` |
| 55% | 6h   | no  | `shorten_optional_workout` |
| 30% | 4.5h | no  | `protect_sleep_window` |
| 35% | 5h   | yes | `protect_tomorrow` |

All four pass in both implementations. The HTML runs a self-test on load (check
the browser console); the Python suite runs via `pytest`.

## Running the Python engine

```bash
python explanation_engine.py 55 6            # text output
python explanation_engine.py 35 5 --exam --json
python -m pytest                             # run the tests
```
