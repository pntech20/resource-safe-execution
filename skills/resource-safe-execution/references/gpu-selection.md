# GPU selection

Establish each evidence level in order:

1. **Device detection:** Confirm that the operating system enumerates a GPU. Treat this only as hardware presence.
2. **Driver/API availability:** Confirm that the required driver and API are available to the current session.
3. **Framework backend availability:** Inspect the actual application's framework and configuration; confirm that its intended CUDA, Metal, DirectML, Vulkan, OpenGL, WebGPU, or other backend is selectable.
4. **Successful test workload:** Run a small representative operation and verify its result with the selected backend or renderer active.
5. **Observed utilization:** Observe device activity and memory during that test. Compare runtime and transfer overhead with the CPU path.

Assign only stages that pass all applicable levels. Keep compilation, parsing, ordinary unit tests, file I/O, and other unsuitable work on the CPU unless the application provides and proves a relevant GPU backend.

For renderer faults, first reproduce the failure under the normal hardware configuration and capture the active renderer. Apply a software fallback only to the failing task, verify the fallback renderer, and record how to restore the original configuration. Restore it during cleanup.
