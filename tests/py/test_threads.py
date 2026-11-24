"""The main thread defines and starts synths while pattern threads compile function instruments.
A race here is rare in a normal build; the TSan build in CI reports it (tests/sanitizers/)."""

import collections
import os
import re
import subprocess

from conftest import SAPF, SAPF_LIB, decode_scgf
from test_patterns import Recorder

# Each instrument builds a SendTrig, a UGen with no outputs, as each main-thread synthdef does.
FN = "\\freq amp sustain [1 0 0 sc.sendtrig pop freq 0 sinosc amp * sustain T]"
DEFS = 100


def test_threads_keep_node_ids_and_def_roots_apart(sapf_bin, tmp_path):
    code = "".join(f"{{:instrument {FN} :midinote [60 64 67] cyc :dur .01}} pbind play pop\n" for _ in range(4))
    # the second start of a def sends a plain /s_new, which the recorder keeps with its node ID
    code += "".join(f"synthdef s{i} [1 0 {i} sc.sendtrig pop 440 sc.sinosc .1 *]\n{{}} s{i} pop {{}} s{i} pop\n"
                    for i in range(DEFS))
    code += ".5 sleep stop .3 sleep\nquit\n"
    r = Recorder()
    try:
        env = dict(os.environ, STAC_SCSYNTH=f"127.0.0.1:{r.port}", STAC_PRELUDE="/dev/null")
        proc = subprocess.run([str(SAPF), "-q", *SAPF_LIB], input=code, capture_output=True, text=True, env=env,
                              timeout=300, cwd=tmp_path)
    finally:
        r.close()
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and "error" not in proc.stdout, out  # TSan exits 66 after a report
    ids = [c[1] for _, _, a, c in r.bundles if a == "/s_new"] + [c[1] for a, c in r.plain if a == "/s_new"]
    assert len(ids) > DEFS
    assert [i for i, n in collections.Counter(ids).items() if n > 1] == []
    mains = [d for d in map(decode_scgf, r.defs) if re.fullmatch(r"s\d+", d["name"])]
    assert len(mains) == DEFS
    foreign = [d["name"] for d in mains if [u[0] for u in d["ugens"]].count("SendTrig") != 1]
    assert foreign == []
