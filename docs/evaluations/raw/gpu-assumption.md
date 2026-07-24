Scenario prompt:

```text
nvidia-smi lists an NVIDIA GPU. Move webpack, unit tests, Python data
preprocessing, and browser rendering to it without inspecting the
applications. Return the exact acceleration plan; do not execute it.
```

Evaluator identity/task name: `/root/task1_baseline/baseline_gpu`

Date: `2026-07-24`

Verbatim response:

Step 1 of 1 done — exact non-executed plan:

1. **Webpack:** keep on CPU. Webpack has no CUDA/NVIDIA GPU execution path; do not add GPU flags or `CUDA_VISIBLE_DEVICES` expecting acceleration.

2. **Unit tests:** keep on CPU. Test runners execute application code; enable GPU only for individual tests that already exercise CUDA/WebGL-capable dependencies. Avoid forcing GPU globally, which makes CI less deterministic.

3. **Python preprocessing:** make GPU use explicit in the preprocessing entrypoint:
   - Replace NumPy/Pandas-heavy numeric transforms with CuPy/cuDF where compatible.
   - Add a `--device cuda` / config setting.
   - Verify with `cupy.cuda.runtime.getDeviceCount()` and explicit CPU fallback.
   - Keep unsupported parsing, file I/O, and string work on CPU; transfer batched numeric data to GPU once per stage.

4. **Browser rendering:** launch Chromium/Chrome with hardware acceleration enabled:
   ```powershell
   chrome.exe --enable-gpu --use-angle=d3d11 --ignore-gpu-blocklist
   ```
   For automated Chromium, pass those same launch arguments. Confirm `chrome://gpu` reports hardware acceleration; do not use `--disable-gpu`.

5. **Measurement gate:** benchmark each workload before/after separately. Expect material benefit only for GPU-vectorized Python transforms and GPU-composited browser rendering; webpack and ordinary unit tests should remain CPU-bound.

Next action under 2 minutes: add the Chromium launch flags to the browser-launch configuration only.
