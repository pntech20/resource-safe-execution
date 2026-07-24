# macOS

## Read-only inspection sources

- Use Activity Monitor and read-only system reports for CPU, memory pressure, swap, disk, process start time, and GPU state.
- Use existing framework or application diagnostics for renderer and backend details.

## Missing-tool behavior

Treat missing optional diagnostics or inaccessible fields as unknown. Use available built-in read-only views, reduce concurrency, and do not install or grant new privileges solely for preflight.

## Backend verification

Confirm that the application exposes the intended Metal or other accelerated backend. Run a small representative operation, inspect the active renderer or backend, and observe GPU activity and memory rather than relying on hardware detection.

## macOS cautions

Use a process group or retained launcher handle where supported. Record a platform process start time and compare it with the PID before cleanup. Respect memory-pressure and thermal signals. Keep renderer overrides task-scoped and restore the normal configuration.

The bundled probe accepts only root-owned diagnostic executables whose canonical ancestors are root-owned, not group/other-writable, and not exposed through a detectable ACL/current-user write grant. Its optional `--output` uses held directory descriptors, no-follow traversal, and exclusive creation so an ancestor swap cannot redirect the file.
