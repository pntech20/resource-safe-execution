# Windows

## Read-only inspection sources

- Use Task Manager, Resource Monitor, Performance Monitor counters, and read-only CIM queries for CPU, memory, paging, disk, process creation time, command line, and parent PID.
- Use vendor utilities or Windows graphics diagnostics only when already available.

## Missing-tool behavior

Treat an unavailable vendor utility, graphics diagnostic, counter, or CIM field as unknown. Continue with built-in read-only sources, choose a more conservative profile, and do not install software merely to complete preflight.

## Backend verification

Inspect the application's reported adapter and backend. For browsers, capture the active graphics feature status and renderer. For compute frameworks, run a small representative operation, confirm the selected backend, and observe GPU utilization and memory.

## Windows cautions

Use a Job Object or retained process handle for child ownership when possible. Record process creation time as the start identity and compare it before cleanup because PIDs are reused. Avoid executable-name-wide termination and system-wide graphics settings. Restore any task-scoped renderer setting after the run.

The bundled probe derives Windows and Program Files roots from native operating-system APIs, rejects reparse or current-token-writable trusted components, ignores inherited `PATH`, and passes only validated root variables to diagnostic children. This protects against unprivileged shadowing, not privileged replacement inside validated system directories. Windows v0.1 rejects `--output`; redirect or capture stdout in a directory whose ownership you have already established.
