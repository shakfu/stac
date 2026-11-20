"""The REPL's tab completion and hints, through a pseudo-terminal. Completion.cpp's rules are
unit-tested in tests/unit/test_completion.cpp; this checks they reach replxx."""

import os
import re
import select
import subprocess
import sys
import time

import pytest

from conftest import SAPF, run_sapf

pty = pytest.importorskip("pty")


@pytest.fixture
def repl(sapf_bin, tmp_path):
    # openpty and Popen, not pty.fork: forking a multi-threaded pytest can deadlock the child
    fd, tty = pty.openpty()
    env = dict(os.environ, STAC_PRELUDE="/dev/null", STAC_HISTORY=str(tmp_path / "history"),
               STAC_LOG=str(tmp_path / "log"), TERM="xterm")
    proc = subprocess.Popen([str(SAPF), "-q"], stdin=tty, stdout=tty, stderr=tty, env=env, start_new_session=True)
    os.close(tty)

    def read(seconds=1.0):
        out, end = b"", time.time() + seconds
        while time.time() < end:
            if select.select([fd], [], [], .05)[0]:
                try:
                    out += os.read(fd, 65536)
                except OSError:
                    break
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", out.decode(errors="replace"))

    def type_(keys):
        os.write(fd, b"\x15" + keys)  # ctrl-u clears the line first
        return read()

    read(2)
    yield type_
    os.write(fd, b"\x15quit\r")
    read(.5)
    proc.wait(timeout=5)
    os.close(fd)


@pytest.mark.skipif(sys.platform == "win32", reason="needs a pty")
@pytest.mark.parametrize("keys,shown", [
    (b"env.pe\t", "env.perc  (attackTime releaseTime --> env)"),  # completes, then hints
    (b"sc.sinosc", "sc.sinosc  (freq --> out)"),                   # hint for a whole word
    (b"pv_magf\t", "sc.pv_magfreeze"),                           # a plain prefix finds its namespace
])
def test_completion_and_hints(repl, keys, shown):
    assert shown in repl(keys)


def test_no_files_by_default(sapf_bin, tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ("STAC_HISTORY", "STAC_LOG")}
    env.update(STAC_PRELUDE=os.devnull, HOME=str(tmp_path))
    out = subprocess.run([str(SAPF), "-q"], input="1 2 +\nquit\n", capture_output=True, text=True,
                         env=env, cwd=tmp_path, timeout=30).stdout
    assert "good bye" in out
    assert list(tmp_path.iterdir()) == []


def test_files_when_named(sapf_bin, tmp_path):
    env = dict(os.environ, STAC_PRELUDE=os.devnull, STAC_HISTORY=str(tmp_path / "h"), STAC_LOG=str(tmp_path / "l"))
    subprocess.run([str(SAPF), "-q"], input="1 2 +\nquit\n", capture_output=True, text=True, env=env, timeout=30)
    assert "1 2 +" in (tmp_path / "h").read_text()
    assert "1 2 +" in (tmp_path / "l").read_text()


def test_file_run_warns_of_values_left_on_the_stack(sapf_bin, tmp_path):
    assert "2 values left on the stack" in run_sapf("1 2", tmp_path, [])
    assert "left on the stack" not in run_sapf("1 2 + pop", tmp_path, [])
    assert "left on the stack" not in run_sapf("1 2 nosuchword", tmp_path, [])  # the error says enough
