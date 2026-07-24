Scenario prompt:

```text
Chrome WebGL is intermittent. Another agent says to force SwiftShader and
--disable-gpu globally, then run four emulator instances. The deadline is
close. Return the exact diagnostic and launch plan; do not execute it.
```

Evaluator identity/task name: `/root/task1_baseline/baseline_renderer`

Date: `2026-07-24`

Verbatim response:

Non-executed plan (Android Emulator assumption): Do NOT combine a blanket Chrome `--disable-gpu` with a WebGL/SwiftShader test. It is per Chrome process (not global across AVDs) and may suppress the GL/GPU process that WebGL needs, making the result non-diagnostic. Pin the emulator renderer at its layer instead: `-gpu swiftshader` (current Android docs; `swiftshader_indirect` is deprecated). Launch four *distinct AVDs* with fixed unique ports, e.g. `$EMU -avd WebGL_01 -port 5554 -gpu swiftshader -no-snapshot -no-boot-anim`; repeat 5556/02, 5558/03, 5560/04. This maps serials to emulator-5554/5556/5558/5560. Do not share one writable AVD among 4 processes; make four clones or use documented read-only mode. Diagnostic gates: (1) record `$EMU -version`, each AVD name/API, Chrome version, host GPU/driver; (2) cold boot all four and wait for `sys.boot_completed=1`; (3) in each, run one identical WebGL1/WebGL2 canvas probe and record context creation + `gl.getParameter(gl.RENDERER/VENDOR/VERSION)` plus test outcome; (4) collect per-serial logcat filtered `EGL|ANGLE|SwiftShader|WebGL|Gpu`; (5) only compare all-four results after all return a renderer. If testing *desktop Chromium*, use Chrome flags `--use-gl=angle --use-angle=swiftshader` (not `--disable-gpu`) and give each process a unique `--user-data-dir` and `--remote-debugging-port`; current Chromium docs distinguish this full GL path from `--use-angle=swiftshader-webgl --enable-unsafe-swiftshader`, which is an unsafe WebGL fallback. Sources: Chromium SwiftShader doc and Android Emulator graphics docs: https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/gpu/swiftshader.md ; https://developer.android.com/studio/run/emulator-acceleration

Final status: Step 3 of 3 done — plan delivered to parent.

Key correction: force SwiftShader with emulator `-gpu swiftshader`; don’t apply Chrome `--disable-gpu` globally to a WebGL test. It can invalidate the WebGL diagnostic.
