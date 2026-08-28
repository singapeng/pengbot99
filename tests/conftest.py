"""Shared paths for the test suite.

The fixture directory is resolved from this file's location rather than from
the process working directory, so the suite runs from anywhere -- previously it
only worked with the working directory set to ``tests``.

Both ``pytest`` and ``python -m unittest discover -s tests`` place this
directory on ``sys.path``, so test modules can import from here under either
runner.
"""

from pathlib import Path

# Directory holding the CSV schedules the tests build their managers from.
# These are test fixtures, not game content: several encode edge cases that
# never ran in the live game.
FIXTURES_DIR = str(Path(__file__).parent / "fixtures")
