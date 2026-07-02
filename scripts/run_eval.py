"""Run the verification loop on the validation set with verbose logging.

Usage: uv run scripts/run_eval.py --limit 10 --budget 15
Real API spend (GPT-5.5, high reasoning). Writes eval_runs/<timestamp>.md. Equivalent to
`uv run ankify eval` plus INFO logging; if the budget runs out mid-run, a partial report
is still written.
"""

from __future__ import annotations

import logging

import fire  # type: ignore[import-untyped]

from ankify.cli import CLI

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    fire.Fire(CLI().eval)
