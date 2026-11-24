"""Wave-table and sound-file buffers: a slot is taken while a graph, Buffer or synth uses it, and free
once the server reports the synth's /n_end. The recorder stands in for scsynth and sends the /n_end."""

import os
import struct
import subprocess
import time
import wave

import pytest
from nanosynth.osc import OscBundle

from conftest import SAPF, SAPF_LIB
from test_patterns import Recorder


@pytest.fixture
def recorder():
    r = Recorder()
    yield r
    r.close()


class Session:
    """stac reading lines one at a time against the recorder."""

    def __init__(self, recorder):
        self.r = recorder
        env = dict(os.environ, STAC_SCSYNTH=f"127.0.0.1:{recorder.port}", STAC_PRELUDE="/dev/null")
        self.proc = subprocess.Popen([str(SAPF), "-q", *SAPF_LIB], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, env=env)

    def send(self, line):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def started(self):
        """The nodes of plays, from the /s_new in each /d_recv's completion."""
        return [m.contents[1] for a, c in self.r.plain if a == "/d_recv" and len(c) > 1 and isinstance(c[1], OscBundle)
                for m in c[1].contents if m.address == "/s_new"]

    def play_and_end(self, line):
        """Sends a line that plays one synth, waits for it to start, then reports its end."""
        before = len(self.started())
        self.send(line)
        deadline = time.monotonic() + 5
        while len(self.started()) == before and time.monotonic() < deadline:
            time.sleep(.01)
        assert len(self.started()) > before, line
        self.r.end(self.started()[-1])
        time.sleep(.05)  # the notification thread releases the slots

    def quit(self):
        return self.proc.communicate("quit\n", timeout=10)[0]

    def plain(self, address):
        return [c for a, c in self.r.plain if a == address]


def table(i):
    return f"#[1 .{i + 10}] 0 0 wavefill"


def test_wave_table_slot_is_reused_after_its_synth_ends(sapf_bin, recorder):
    s = Session(recorder)
    for i in range(25):  # 17 slots
        s.play_and_end(f"[100 0 {table(i)} osc 0 *] stac.play pop")
    out = s.quit()
    assert "error" not in out, out
    assert {c[0] for c in s.plain("/b_alloc")} == set(range(512, 542)), out


def test_wave_table_slots_run_out_rather_than_overwrite(sapf_bin, recorder):
    s = Session(recorder)
    for i in range(18):  # each graph bound to a name keeps its slot
        s.send(f"[100 0 {table(i)} osc 0 *] = g{i}")
    out = s.quit()
    assert out.count("osc : more than 17 wave tables in use") == 1, out


def test_synthdef_loads_its_wave_table(sapf_bin, recorder):
    s = Session(recorder)
    s.send(f"synthdef wt [100 0 {table(0)} osc .1 *]\n{{}} wt pop")
    out = s.quit()
    addresses = [a for a, _ in recorder.plain]
    assert "error" not in out, out
    assert addresses.count("/b_alloc") == 30 and addresses.index("/b_alloc") < addresses.index("/d_recv"), out


@pytest.fixture
def wavs(tmp_path):
    paths = []
    for i in range(70):
        path = tmp_path / f"f{i}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(struct.pack("<480h", *[0] * 480))
        paths.append(path)
    return paths


def test_sound_file_slot_is_reused_after_its_synth_ends(sapf_bin, recorder, wavs):
    s = Session(recorder)
    for path in wavs:  # 64 slots
        s.play_and_end(f'["{path}" sf> .001 *] stac.play pop')
    out = s.quit()
    assert "error" not in out, out
    assert {c[0] for c in s.plain("/b_allocRead")} == {0}, out


def test_buffer_free_keeps_a_file_a_synth_plays(sapf_bin, recorder, wavs):
    s = Session(recorder)
    s.send(f'"{wavs[0]}" buffer.read = b')
    s.send(f'["{wavs[0]}" 1 1 playbuf .001 *] stac.play pop')
    s.send('"x" pr cr')
    time.sleep(.3)
    s.send("b.free")  # the synth still holds the slot: no /b_free
    time.sleep(.2)
    freed_while_playing = len(s.plain("/b_free"))
    s.r.end(s.started()[-1])
    time.sleep(.05)
    s.send(f'"{wavs[0]}" buffer.read = b2 b2.free')  # the last holder frees the buffer
    out = s.quit()
    assert "error" not in out, out
    assert (freed_while_playing, len(s.plain("/b_free"))) == (0, 1), out
