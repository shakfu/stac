"""examples/sapf.stac writes the same defs from two builds. C++ leaves argument evaluation order
unspecified, so gcc and clang builds once differed in UGen order and random draws (docs/dev/ssp.md,
task 2). CI's Ubuntu job sets STAC_OTHER to a clang build of its gcc one; without it, the parity test
skips. The determinism test compares two runs of the same build."""

import functools
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from conftest import ROOT, SAPF, SAPF_LIB, graph, scgf_blobs

OTHER = os.environ.get("STAC_OTHER")

# Each play writes example N's score to eN.osc, then resets the seed for the next example.
HARNESS = """0 R = _n
\\x [_n get 1 + _n set  x 2 ["e" _n get] "" strcat >nrt  0 setseed] = play
\\x n [] = >sfo
\\x n [] = >sf
0 setseed
"""


def examples() -> str:
    """examples/sapf.stac without its Project Euler and Rosetta Code section: 38 s of computation, no play."""
    lines = (ROOT / "examples" / "sapf.stac").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if "programming examples from Project Euler" in l) - 1
    roman = next(i for i, l in enumerate(lines) if "Roman_numerals" in l)
    end = next(i for i in range(roman, len(lines)) if re.fullmatch(r";+", lines[i]))
    assert not any("play" in l.split(";")[0] for l in lines[start:end]), "the skipped section has a play"
    return "\n".join(lines[:start] + lines[end:])


@functools.cache
def scores(stac: Path, run: int = 0) -> dict[int, list[str]]:
    """Each example's defs, as graphs, by example number; `run` keys separate runs of one build."""
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, STAC_SYNTHDEFS=d, STAC_RECORDINGS=d, STAC_PRELUDE="/dev/null", STAC_HISTORY=f"{d}/history",
                   STAC_SCSYNTH="127.0.0.1:1")
        out = subprocess.run([str(stac), "-q", *SAPF_LIB], input=HARNESS + examples() + "\nquit\n", capture_output=True,
                             text=True, env=env, timeout=120, cwd=d).stdout
        errors = [l for l in out.splitlines() if l.startswith(("error", "syntax error"))]
        assert errors == [], errors
        return {int(p.stem[1:]): [graph(b) for b in scgf_blobs(p.read_bytes())] for p in Path(d).glob("e*.osc")}


def same_defs(a: dict[int, list[str]], b: dict[int, list[str]]):
    assert len(a) >= 150, len(a)
    assert a.keys() == b.keys()
    differ = [n for n in sorted(a) if a[n] != b[n]]
    first = next(((n, x, y) for n in differ for x, y in zip(a[n], b[n]) if x != y), None)
    assert differ == [], f"examples {differ} (Nth play in examples/sapf.stac) differ; first def:\n{first}"


def test_examples_write_deterministic_defs(sapf_bin):
    same_defs(scores(SAPF), scores(SAPF, 1))


@pytest.mark.skipif(not OTHER, reason="STAC_OTHER names no second build")
def test_examples_write_the_same_defs_across_compilers(sapf_bin):
    same_defs(scores(SAPF), scores(Path(OTHER)))
