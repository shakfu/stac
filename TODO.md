# TODO

In order of priority within each section. Design records are in docs/dev/; this file lists work only.

## Medium

### Language

- [ ] Check on a gcc build that the six examples of docs/dev/ssp.md task 2, e.g. `rocks on rails`, now write the same defs as clang. A scan for calls with two node-building arguments found six sites and fixed them; whether they cover all six examples is untested.

- [ ] `stactool.py lint`: warn on a `def` without `-->` in a library file (docs/dev/stac.md, Proposal: unified definitions, open question 1).

- [ ] Dictionary: say that a zero-output UGen (Out, OffsetOut, ReplaceOut, XOut, LocalOut, SharedOut, SendTrig, AnalogOut, DigitalOut, BelaScopeOut) leaves a root, not a channel. Three parts: `gen_ugens.py` writes `--> root` as the effect of a zero-output class; one sentence in each of the 10 entries; a `localout` example with `play`.

### Namespaces and modules

- [ ] `sc3p`: sc3-plugins' UGens. Needs a spec in `sclang-reference.json`'s format, from sclang with the plugins installed, and the plugin binaries in the embedded scsynth and on the SSP (docs/dev/stac.md, Proposal: canonical namespaces and import).

- [ ] Custom UGens: read a spec file at run time into a namespace, so stac need not be rebuilt for a user's own UGens.

- [ ] Module reload is noticed when an `import` runs. A file watcher could reload on save; decide whether a half-saved file loading by itself is acceptable.

### Server objects

- [ ] `>sd` and `.write`: write the SSP `scsy` sidecar's `@p` lines alongside `name.scsyndef`.
  - Format, from `../ssp/plugins/scsynth/README.md`: `name.txt` beside `name.scsyndef`, lines `// @p1 cutoff 20 20000 Hz log cv 3` (slot, control name, min, max, unit, curve, CV input).
  - Without a sidecar, `scsy` maps `p1`..`p16` to the first 16 controls in def order, each ranged 0 to max(1, 2 x default). A sidecar is needed only for ranges, units, curves, CV or another slot order.
  - Open: where min, max and curve come from. Neither `ctl` nor a `synthdef` control declares them.
  - Open: slot order. `synthdef` keeps declaration order; `>sd` sorts parameters by name.
  - Note: a label that names no control fails the load in `scsy`, and `freq`, `velocity` and `gate` are reserved for MIDI.

### Editor and REPL

- [ ] Editor plugin for stac files: nvim first, with `tree-sitter-stac/queries/highlights.scm` so files take the editor theme's colours. Add `locals.scm`, `indents.scm` and `injections.scm`, which the REPL does not need. `STAC_COLORS` stays the REPL's interim override, not a theme system.

- [ ] REPL highlighting parses each continuation line alone, so a `[` or `def` opened on an earlier line is not seen.

- [ ] UGen colouring covers only words of the namespace `sc`. sapf's oscillators under `-p sapf.stac` are functions and show as library words. Decide whether "UGen" means any signal generator; that needs a tag in the dictionary, not a type test.

- [ ] No differential test between `tree-sitter-stac` and `stactool.py`'s lexer; they could split a token differently and nothing would fail.

### sapf words

- [ ] `lpcombc` (10 examples): its low pass sits inside the feedback loop, which needs single-sample feedback. Options: an approximation, or a plugin UGen.

- [ ] Unmapped sapf words, by examples blocked: `violet` 5, `pdiv` 3, `par`, `octenv`, `quadenv`, `vsaw`, `gray`, and about a dozen with one or two uses. `klang`, `blip`, `crackle`, `hilbert` and `fft` exist in `sc` with SC's arguments. The mouse controls are excluded on purpose.

## Low

- [ ] Imports by category, such as `import sc.* in demand`. Left out until a prelude needs one.

- [ ] Revisit `where` once modules have been used: helpers private to one definition may still clutter a module (docs/dev/stac.md and the discussion of 2026-10-16).

- [ ] A redefined word adds a second help line; `helpall` lists both, though `--words` keeps the last.

- [ ] `ola` voices start on the 64-frame block holding their time. `OffsetOut` would place them on the frame but crashed nanosynth's NRT renderer (`world_nrt_render`); find out why.

- [ ] Samples load only from WAV or AIFF files.

- [ ] The Windows branches, e.g. `>sfo`'s `start`, are untested.

- [ ] Report the 17 bugs in original sapf, docs/dev/upstream-sapf-bugs.md, upstream; undecided.

- [ ] Pack tests/fixtures/ref, 3.6 MB of WAV, into one `.npz`.
