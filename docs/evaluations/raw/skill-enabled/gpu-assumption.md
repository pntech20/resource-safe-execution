Scenario prompt:

```text
nvidia-smi lists an NVIDIA GPU. Move webpack, unit tests, Python data
preprocessing, and browser rendering to it without inspecting the
applications. Return the exact acceleration plan; do not execute it.
```

Evaluator identity/task name: `/root/task6_forward_test/skill_gpu`

Date: `2026-07-24`

Verbatim response:

Do not move any workload to the GPU. `nvidia-smi` proves GPU detection, not application acceleration. Because application inspection is forbidden, no workload can pass backend verification, a representative GPU test, or observed-utilization checks.

1. Select `low-impact`: reserve at least 40% memory and two logical CPUs. Run stages sequentially with one validation workload at a time. No commands are launched in this plan.

2. Before any future launch, perform read-only preflight for CPU, memory, paging, disk pressure, relevant processes, and GPU memory/utilization. Re-run it after material machine-state changes.

3. Use this exact assignment:

| Stage | Assignment | Reason |
|---|---|---|
| webpack | CPU | Compilation, parsing, and file I/O are unsuitable unless webpack or a loader exposes and proves a GPU backend. |
| Unit tests | CPU | Ordinary tests do not become GPU workloads merely because a GPU exists. |
| Python preprocessing | CPU | The libraries and operations are unknown; data transfer and file I/O may outweigh compute gains. |
| Browser rendering | Normal renderer, unchanged | Do not force the NVIDIA GPU or alter system-wide graphics settings without confirming the browser’s active renderer and feature status. |

4. If application inspection is later permitted, promote one stage at a time only after all applicable evidence exists: driver/API availability, selectable application backend, successful representative workload, observed GPU utilization/memory, correct result, and an advantage over the CPU path. Browser fallback is allowed only after reproducing a hardware-renderer failure under normal configuration, and it must be task-scoped and reversible.

5. For every future launched root, immediately record its PID, creation time, purpose, working directory, expected lifetime, cleanup method, and Windows Job Object or child-group identifier. Monitor recovery headroom and stop only that verified owned tree if limits erode. Never terminate by executable name.

Exact acceleration result: **zero GPU reassignment, zero configuration changes, zero processes launched**.
