# TODO

In order of priority within each section. Design records are in docs/dev/; this file lists work only.

## High

Open findings of REVIEW.md (2026-11-23); its numbers are in brackets.

- [ ] Roll back a failed line [9]. Runtime binds write `th.mWorkspace` at once and `import` binds at compile time; nothing reverts `mWorkspace`, `mImported` or `mConsts` on error. Snapshot them before compile and restore in the catch, as `Consts` does in `Modules.cpp`. First merge the two copies of the bind body in `Opcode.cpp` (`:170-186`, `:205-218`).

- [ ] Lock `gNdefs` [6]. The evaluator inserts into the `std::map` (`PatternOps.cpp` `ndef_`) while `stopEventStreams` iterates it from the CLAP main thread on deactivate or Stop.

- [ ] `Events::defNamed` returns a raw `Def*` [6]. A pattern thread keeps it in `events.defs`; redefining the name on the main thread can free it. Keep a `P<Def>`.

- [ ] `stop` races event-stream sends [11]. `run()` checks `live()`, then sends without a lock, so a `/s_new` 0.2 s ahead can land after `/clearSched` and `/g_deepFree`. `Texture.cpp` closes the same window with `gPendingMutex`.

- [ ] `stopHost` waits for the audio thread after `World_Cleanup` [10]; move the wait between nulling `hostWorld_` and the cleanup.

- [ ] Saved CLAP state turns on the loopback UDP listener [15], which runs any local sender's code. Do not restore UDP from state, or require a token.

## Medium

### Language

- [ ] `stactool.py lint`: warn on a `def` without `-->` in a library file (docs/dev/stac.md, Proposal: unified definitions, open question 1).

- [ ] Dictionary: say that a zero-output UGen (Out, OffsetOut, ReplaceOut, XOut, LocalOut, SharedOut, SendTrig, AnalogOut, DigitalOut, BelaScopeOut) leaves a root, not a channel. Three parts: `gen_ugens.py` writes `--> root` as the effect of a zero-output class; one sentence in each of the 10 entries; a `localout` example with `play`.

- [ ] Decide `.ar` on a `kr` UGen: raise it with `K2A`, or reject it (docs/dev/stac.md, open question 2).

- [ ] Decide `render`'s duration: explicit only, as built, or inferred when every channel has a `doneAction` (docs/dev/stac.md, open question 3). Inference would not break the explicit form.

### Namespaces and modules

- [ ] The 19 SC classes not generated (docs/dev/stac.md, phase 2; reasons in `spec/stac-ugens.json`). `Splay` and `DynKlank` first: SC pieces use them most.
  - sclang code that emits other UGens: `Changed`, `CompanderD`, `HilbertFIR`, `VarLag`, `Splay`, `SplayAz`, `DynKlank`, `DynKlang`, `Dunique`, `LocalBuf`, `Tap`, `UnpackFFT`, `InBus`; `Dstutter` is a deprecated alias of `Ddup`.

  - strings or other objects as arguments: `Poll`, `Dpoll`, `SendReply`, `SendPeakRMS`, `InRect`.

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

- [ ] `stop` against a remote scsynth can let an `ola` voice start after it. Voice sends and `/clearSched` rely on packets arriving in send order, which holds for the embedded server and loopback, not across a network. One option: voices in a group that `stop` frees, so a late `/s_new` finds no target.

### SSP

- [ ] Task 1 of docs/dev/ssp.md, the `sapf` live-coding plugin: steps 2 and 4 need `ScsynthServer::now()`, a `post` hook and an interrupt flag.

### Editor and REPL

- [ ] Editor plugin for stac files: nvim first, with `tree-sitter-stac/queries/highlights.scm` so files take the editor theme's colours. Add `locals.scm`, `indents.scm` and `injections.scm`, which the REPL does not need. `STAC_COLORS` stays the REPL's interim override, not a theme system.

- [ ] REPL highlighting parses each continuation line alone, so a `[` or `def` opened on an earlier line is not seen.

- [ ] UGen colouring covers only words of the namespace `sc`. sapf's oscillators under `-p sapf.stac` are functions and show as library words. Decide whether "UGen" means any signal generator; that needs a tag in the dictionary, not a type test.

- [ ] No differential test between `tree-sitter-stac` and `stactool.py`'s lexer; they could split a token differently and nothing would fail.

### sapf words

- [ ] `lpcombc` (10 examples): its low pass sits inside the feedback loop, which needs single-sample feedback. Options: an approximation, or a plugin UGen.

- [ ] Unmapped sapf words, by examples blocked: `violet` 5, `pdiv` 3, `par`, `octenv`, `quadenv`, `vsaw`, `gray`, and about a dozen with one or two uses. `klang`, `blip`, `crackle`, `hilbert` and `fft` exist in `sc` with SC's arguments. The mouse controls are excluded on purpose.

### Concurrency and lifetime

- [ ] `go` threads are detached and untracked [7]; `stopPlayers` waits only for event streams and `ola` schedulers. `gPostHandler` is a plain `std::function` that `setPostHandler` replaces while threads may `post`.

- [ ] CLAP main thread blocks up to 10 s [14]: `UdpServer::stop()` joins a thread waiting in `evalFromUdp` (`kUdpReplyTimeout`). Triggers: toggling UDP, `loadState`, `destroy`.

- [ ] A play's 30 wave-table loads go to a UDP server as 1.2 MB at once and can overflow its receive buffer; the test stand-in dropped them until its buffer was raised. Pace the loads, or send them in a sync per few tables.

- [ ] `ola` voices send with `scsynthSend`, which ignores a failed send, so a voice can go missing silently [12].

- [ ] `Def::mSent` never resets [6]. After a host's `stopHost`/`startHost` or an external server's restart, a def's `/s_new` goes out without `/d_recv` and fails.

- [ ] Slot holds of a server that sends no notifications, or of a restarted UDP server, are never released; the pools then fill and raise errors. Release them when a UDP server's `/notify` registration is lost.

- [ ] Def leaks left in step 4: a pattern stopped with `.stop`, then a global `stop` within 0.2 s, drops its timed `/d_free` bundle (up to 64 defs); an uncached function-instrument event scheduled but dropped by `/clearSched` keeps its def.

- [ ] NRT scores (`score`, `>nrt`) do not include a `synthdef`'s wave-table and sound-file loads (`Def::mLoads`).

### Interpreter

- [ ] Closures resolve own-scope names in the caller's workspace [19]: `pushWorkspace 5 = h \[h] popWorkspace = g`, then `g !` gives "not found: h". `docs/dev/stac.md:340-343` describes the old behaviour; fix one or the other.

- [ ] Modules are cached by name but reused by path [18]: two `util.stac` in different directories reload on every import, with their importers, and each reload adds a `ScopeView` to `mOtherScopes` that is never removed.

### CI and tests

- [ ] Check the `sanitize` CI job's first run on Linux: the `vm.mmap_rnd_bits=28` step, the Linux suppression patterns (`_UGens`, `pa_`) and the CLAP ctest, which timed out once under TSan locally.

- [ ] Linux CI skips about 35 more tests than macOS, likely the real-server ones in `test_play*.py` and `test_sf.py` [16]. Run a server without an audio device, or a dummy ALSA device.

- [ ] Install the tree-sitter CLI in CI, so `test_grammar.py` stops skipping and checks `parser.c` against `grammar.js` [16].

- [ ] Turn on `-Wall -Wextra` and fix or suppress what they report; document that `CMAKE_CXX_FLAGS_RELEASE "-O3"` keeps `assert` live [17].

- [ ] stac's output to a pipe is block-buffered, so `live()` in `test_patterns.py` times its steps from process start; three tests are marked `timing` for that. Flush after each REPL line, then wait for a ready line.

## Low

- [ ] Imports by category, such as `import sc.* in demand`. Left out until a prelude needs one.

- [ ] Revisit `where` once modules have been used: helpers private to one definition may still clutter a module (docs/dev/stac.md and the discussion of 2026-10-16).

- [ ] A redefined word adds a second help line; `helpall` lists both, though `--words` keeps the last.

- [ ] `ola` voices start on the 64-frame block holding their time. `OffsetOut` would place them on the frame but crashed nanosynth's NRT renderer (`world_nrt_render`); find out why.

- [ ] Samples load only from WAV or AIFF files.

- [ ] The Windows branches, e.g. `>sfo`'s `start`, are untested.

- [ ] Report the 17 bugs in original sapf, docs/dev/upstream-sapf-bugs.md, upstream; undecided.

- [ ] Pack tests/fixtures/ref, 3.6 MB of WAV, into one `.npz`.

- [ ] From REVIEW.md's Low list:
  - `FunDef::mWorkspace` and `Fun::mWorkspace` are written, never read, and keep compile-time snapshots alive.
  - `lookupTop` reads `current()` and `version()` in two steps, and module scopes refresh per lookup, so one event can mix module versions.
  - `getsym` interns every help line and every hint prefix; the symbol table never shrinks.
  - The OSC reply parsers (`Scsynth.cpp` `getString`, `EmbeddedServer.cpp` `oscString`) throw `out_of_range` on a short packet.
  - `patch-supercollider.sh` cannot detect a patch that no longer matches; check each edit with `grep -q`.
  - CLAP editor: a lone `\` in a string counts as an escape, unlike `Parser.cpp`; an unmatched opener disables grouping below it (`editor_logic.cpp:37-51`).
  - CLAP `init()` appends to `STAC_PATH` per instance and calls `setenv` while host threads may call `getenv`.
  - CLAP UDP replies have no size cap; over 65507 bytes `sendto` fails silently.
  - Parser UB: `1LL << level` unbounded (`Parser.cpp:314-350`); hex and stack-effect parsing overflow signed integers.
  - `dictionary.py sync` drops prose between `##` and the first `###` (`elif entries:`).
  - `stactool fmt`: `--indent -1` strips indentation, `--indent x` raises; the repo's own `.stac` files fail `fmt --check`.
  - Conformance: loose RMS bounds (`ola_sine` .08, `resonz` .06, `klank` .04), 0.1 s renders, and 194 of 197 references from a sapf build that is gone.
  - No dedicated tests for `RandomOps.cpp` or `SetOps.cpp`, and no seeded-noise conformance case.
  - `test_play.py` uses fixed ports 57193 and 57199 and asserts after sleeps.
  - Doc drift: CHANGELOG says 46 and 48 `sapf.stac` definitions; 1330 dictionary entries is now 1332; 181 entries lack an example; README links `../nanosynth`.
  - Housekeeping: `project(sapf_sc)`, the `SAPF_*` CMake options and the `pyproject.toml` name; unused `tests/run_file_test.cmake` and `tests/test_startup_debug.cpp`; `.gitignore`'s `*.mod*`; CI actions pinned by tag, not SHA; `uv run` without `--locked`.
