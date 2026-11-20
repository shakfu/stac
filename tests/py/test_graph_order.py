"""UGen order must not depend on the compiler. C++ leaves the order in which a call's arguments
are evaluated unspecified; a graph helper that built two nodes in one call's arguments gave gcc and
clang builds different defs. The expected orders come from a clang build; CI's Ubuntu job checks gcc."""

import pytest

from conftest import decode_scgf


def graph(scgf: bytes) -> str:
    def ref(x):
        return f"{x[1]:g}" if x[0] == "c" else f"#{x[0]}.{x[1]}" if x[1] else f"#{x[0]}"
    return " ".join(f"{name}{'/' + str(special) if special else ''}({','.join(ref(x) for x in inputs)})"
                    for name, _, special, inputs, _ in decode_scgf(scgf)["ugens"])


ORDERS = {
    "100 0 saw 1k 1 'bw ctl bpf":
        'Control() BinaryOpUGen/2(#0.1,0.5) BinaryOpUGen/25(2,#1) UnaryOpUGen(#1) BinaryOpUGen/25(2,#3) BinaryOpUGen/1(#2,#4) LFSaw(100,0) BPF(#6,1000,#5) Out(#0,#7)',
    "100 0 saw 1k 1 'bw ctl bsf":
        'Control() BinaryOpUGen/2(#0.1,0.5) BinaryOpUGen/25(2,#1) UnaryOpUGen(#1) BinaryOpUGen/25(2,#3) BinaryOpUGen/1(#2,#4) LFSaw(100,0) BRF(#6,1000,#5) Out(#0,#7)',
    "100 0 saw 1k 'f ctl lpf1":
        'Control() BinaryOpUGen/2(#0.1,6.28319) LFSaw(100,0) SampleRate() BinaryOpUGen/4(#1,#3) UnaryOpUGen/29(#4) BinaryOpUGen/1(2,#5) BinaryOpUGen/2(#6,#6) BinaryOpUGen/1(#7,1) UnaryOpUGen/14(#8) BinaryOpUGen/1(#6,#9) BinaryOpUGen/1(1,#10) BinaryOpUGen/2(#11,0.5) FOS(#2,#12,#12,#10) Out(#0,#13)',
    "100 0 saw 1k 'f ctl hpf1":
        'Control() BinaryOpUGen/2(#0.1,6.28319) LFSaw(100,0) SampleRate() BinaryOpUGen/4(#1,#3) UnaryOpUGen/29(#4) BinaryOpUGen/1(2,#5) BinaryOpUGen/2(#6,#6) BinaryOpUGen/1(#7,1) UnaryOpUGen/14(#8) BinaryOpUGen/1(#6,#9) BinaryOpUGen(#10,1) BinaryOpUGen/2(#11,0.5) UnaryOpUGen(#12) FOS(#2,#12,#13,#10) Out(#0,#14)',
    "100 0 saw 1k 'f ctl lpf2":
        'Control() BinaryOpUGen/13(#0.1,0.001) BinaryOpUGen/2(#1,6.28319) LFSaw(100,0) SampleRate() BinaryOpUGen/4(#2,#4) UnaryOpUGen/29(#5) BinaryOpUGen/1(1,#6) BinaryOpUGen/2(#7,0.5) BinaryOpUGen/2(#6,-2) UnaryOpUGen(#9) UnaryOpUGen(#9) UnaryOpUGen/28(#5) BinaryOpUGen/2(#12,0.707107) BinaryOpUGen/1(1,#13) UnaryOpUGen(#14) UnaryOpUGen(#14) BinaryOpUGen(#13,1) BinaryOpUGen/4(#8,#17) BinaryOpUGen/4(#7,#17) BinaryOpUGen/4(#8,#17) BinaryOpUGen/4(#10,#17) BinaryOpUGen/4(#15,#17) SOS(#3,#18,#19,#20,#21,#22) BinaryOpUGen/4(#8,#17) BinaryOpUGen/4(#7,#17) BinaryOpUGen/4(#8,#17) BinaryOpUGen/4(#11,#17) BinaryOpUGen/4(#16,#17) SOS(#23,#24,#25,#26,#27,#28) Out(#0,#29)',
    "100 0 saw 1k 'f ctl hpf2":
        'Control() BinaryOpUGen/13(#0.1,0.001) BinaryOpUGen/2(#1,6.28319) LFSaw(100,0) SampleRate() BinaryOpUGen/4(#2,#4) UnaryOpUGen/29(#5) BinaryOpUGen/1(-1,#6) BinaryOpUGen/2(#7,-0.5) BinaryOpUGen/2(#6,-2) UnaryOpUGen(#9) UnaryOpUGen(#9) UnaryOpUGen/28(#5) BinaryOpUGen/2(#12,0.707107) BinaryOpUGen/1(1,#13) UnaryOpUGen(#14) UnaryOpUGen(#14) BinaryOpUGen(#13,1) BinaryOpUGen/4(#8,#17) BinaryOpUGen/4(#7,#17) BinaryOpUGen/4(#8,#17) BinaryOpUGen/4(#10,#17) BinaryOpUGen/4(#15,#17) SOS(#3,#18,#19,#20,#21,#22) BinaryOpUGen/4(#8,#17) BinaryOpUGen/4(#7,#17) BinaryOpUGen/4(#8,#17) BinaryOpUGen/4(#11,#17) BinaryOpUGen/4(#16,#17) SOS(#23,#24,#25,#26,#27,#28) Out(#0,#29)',
    "100 0 saw .01 .01 1 'd ctl combn":
        'Control() BinaryOpUGen/4(0.01,#0.1) UnaryOpUGen/5(#1) BinaryOpUGen/12(#2,2) BinaryOpUGen/25(0.001,#3) UnaryOpUGen/11(#1) BinaryOpUGen/2(#5,#4) LFSaw(100,0) CombN(#7,0.01,0.01,#0.1) BinaryOpUGen/2(#8,#6) Out(#0,#9)',
    "100 0 saw .01 .01 1 'd ctl combc":
        'Control() BinaryOpUGen/4(0.01,#0.1) UnaryOpUGen/5(#1) BinaryOpUGen/12(#2,2) BinaryOpUGen/25(0.001,#3) UnaryOpUGen/11(#1) BinaryOpUGen/2(#5,#4) LFSaw(100,0) CombC(#7,0.01,0.01,#0.1) BinaryOpUGen/2(#8,#6) Out(#0,#9)',
    '0 1 1 line':
        'Control() Line(1,1,0,0) SampleRate() BinaryOpUGen/2(0,#2) BinaryOpUGen(#3,0.5) UnaryOpUGen/9(#4) BinaryOpUGen/1(#5,0.5) SampleDur() BinaryOpUGen/2(#6,#7) EnvGen(1,1,0,1,2,1,2,-99,-99,1,#8,1,0,0,0,1,0) BinaryOpUGen/2(#1,#9) BinaryOpUGen/2(#10,#9) Out(#0,#11)',
    '100 0 sinosc .1 T':
        'Control() SinOsc(100,0) SampleRate() BinaryOpUGen/2(0.1,#2) BinaryOpUGen(#3,0.5) UnaryOpUGen/9(#4) BinaryOpUGen/1(#5,0.5) SampleDur() BinaryOpUGen/2(#6,#7) EnvGen(1,1,0,1,2,1,2,-99,-99,1,#8,1,0,0,0,1,0) BinaryOpUGen/2(#1,#9) BinaryOpUGen/2(#10,#9) Out(#0,#11)',
}


@pytest.mark.parametrize("expr", ORDERS)
def test_ugen_order(compile_sapf, expr):
    assert graph(compile_sapf(expr)) == ORDERS[expr]
