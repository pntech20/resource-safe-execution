# Linux

## Read-only inspection sources

- Use `/proc`, `/sys`, `ps`, `free`, `vmstat`, `df`, and existing vendor tools for CPU, memory, paging, disk, process start ticks, cgroups, and GPU state.
- Read pressure stall information when the kernel exposes it.

## Missing-tool behavior

Treat missing commands, vendor tools, kernel files, permissions, or container-visible metrics as unknown. Fall back to available read-only pseudo-files, choose a more conservative profile, and do not install packages merely for preflight.

## Backend verification

Inspect the application's selected CUDA, ROCm, Vulkan, OpenGL, WebGPU, or other backend. Run a small representative operation and observe the active renderer, device utilization, and device memory.

## Linux cautions

Prefer a dedicated process group, session, cgroup, container, or retained launcher handle. Record `/proc/<pid>/stat` start ticks or an equivalent platform start identity and compare it before cleanup. Account for container quotas rather than host totals. Keep software-renderer environment changes task-scoped and restore normal configuration.

The bundled probe accepts only root-owned diagnostic executables whose canonical ancestors are root-owned, not group/other-writable, and not exposed through a detectable ACL/current-user write grant. Its optional `--output` uses held directory descriptors, no-follow traversal, and exclusive creation so an ancestor swap cannot redirect the file.
