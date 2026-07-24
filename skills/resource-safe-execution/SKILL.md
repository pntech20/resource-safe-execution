---
name: resource-safe-execution
description: Use when planning, launching, monitoring, or cleaning up CPU-, memory-, disk-, GPU-, browser-, emulator-, or process-intensive work on Windows, macOS, or Linux.
---

# Resource Safe Execution

Preserve recovery headroom, prove acceleration, and track process ownership before starting resource-intensive work.

## Core workflow

Follow the numbered sections in order. Re-run preflight after a material workload or machine-state change.

## 1. Preflight

1. Run the [resource probe](scripts/resource_probe.py) for a minimal read-only host-inspection snapshot.
2. Inspect current CPU, memory, paging, disk space and pressure, relevant processes, and GPU state with platform read-only sources.
3. Record the task directory, intended commands, expected duration, interactive-use needs, and recovery constraints.
4. Treat probe recommendations as conservative guidance. Reduce work further when the machine remains unresponsive.

The probe performs read-only host inspection unless an explicit `--output` path requests its optional output-file write. That write creates a new file exclusively and refuses an existing path or symlink. The probe never terminates pre-existing or unrelated processes; it may stop only its own diagnostic child when the five-second timeout or one-MiB combined-output bound overflows. This guidance is not permission to launch or terminate workload processes.

## 2. Classify the workload

Classify each stage as CPU-, memory-, disk-, GPU-, browser-, emulator-, or process-intensive. Separate stages that can run sequentially. Identify whether the application actually exposes an accelerated backend; account for device-memory capacity, transfer costs, and contention. Keep unsuitable work on the CPU.

## 3. Choose a profile

- `low-impact`: preserve at least 40 percent memory and two logical CPUs.
- `balanced`: preserve at least 25 percent memory and one logical CPU.
- `throughput`: use measured capacity while retaining one recovery CPU and enough memory to avoid paging.

Choose `low-impact` for an interactive, unstable, thermally constrained, or already pressured machine. Choose `balanced` only after a stable preflight. Choose `throughput` only for an attended run with measured capacity, monitoring, and a bounded rollback path. Cap worker and instance counts explicitly; do not infer safety from the requested parallelism.

## 4. Verify acceleration

Use the evidence ladder in [GPU selection](references/gpu-selection.md). Reproduce a suspected hardware-renderer failure under normal configuration before enabling a fallback. Verify the active renderer or framework backend with a small representative workload and observed utilization.

If hardware acceleration fails, scope software rendering or another fallback to the single task. Record the original configuration and restore normal configuration during cleanup. Never treat device detection alone as proof that a workload uses the device.

## 5. Own launched processes

Create the ownership record defined in [process lifecycle](references/process-lifecycle.md) immediately after launch. Capture the root PID, platform start identity, purpose, working directory, expected lifetime, cleanup method, and child-group identifier.

Use process-group, job-object, or owned-tree facilities when available. Before signaling or terminating, re-read the process and verify both its PID and start identity. Treat a PID mismatch, reused PID, unavailable identity, or unexpected command context as unowned until investigated.

## 6. Monitor and adapt

Monitor CPU saturation, available memory, paging, disk pressure, GPU memory and utilization, responsiveness, errors, and owned-process health at bounded intervals. Lower worker counts, pause stages, or stop the owned group when recovery headroom erodes. Re-run preflight before resuming.

## 7. Clean up

Stop only the verified owned process group or tree with its recorded cleanup API. Refuse executable-name-wide cleanup, even under time or resource pressure. Verify exit, retain relevant logs, remove task-scoped temporary state, and restore renderer or backend configuration changed for the task. Leave persistent processes running only when the ownership record declares them persistent.

When cleanup is requested without an ownership record, the response must still give this conditional safe procedure: locate the task-scoped ownership record, identify its owned root and group, verify the root PID plus start identity, invoke only the recorded graceful cleanup and owned-group or owned-tree termination APIs, then verify exit. If any step lacks evidence, refuse termination and name the missing evidence; never substitute executable-name commands.

## Non-negotiable safeguards

- Keep host inspection read-only until the launch plan, resource profile, and ownership record are defined; treat an explicitly requested probe output file as task-scoped state.
- Bound concurrency and preserve the selected profile's recovery headroom.
- Reject broad termination by executable name; identify an owned root and verify its start identity first.
- Reproduce hardware-renderer failure before fallback, verify the active renderer, scope fallback to the task, and restore normal configuration.
- Stop or reduce work when the system remains unresponsive despite conservative recommendations.

## References

- Read [GPU selection](references/gpu-selection.md) before assigning work to a GPU or changing a renderer.
- Read [process lifecycle](references/process-lifecycle.md) before launching, tracking, or cleaning up processes.
- Read the platform guide for [Windows](references/windows.md), [macOS](references/macos.md), or [Linux](references/linux.md) before choosing inspection and ownership APIs.
- Run the [resource probe](scripts/resource_probe.py) for the minimal portable read-only host-inspection snapshot.
