# Process lifecycle

Create one ownership record per launched root:

```json
{
  "root_pid": 1234,
  "start_identity": "platform start time",
  "purpose": "bounded description",
  "working_directory": "task directory",
  "expected_lifetime": "task or persistent",
  "cleanup_method": "owned process or process-group API",
  "child_group": "identifier or unavailable"
}
```

Capture the record immediately after launch. Prefer a Windows Job Object, POSIX process group or session, container, or launcher handle that provides explicit child ownership. Store task-scoped records beside task logs.

Before cleanup, inspect the root again and compare both `root_pid` and `start_identity`. Also check purpose, working directory, and command context when available. If identity cannot be verified, do not terminate it as owned. Investigate or request direction.

Signal the recorded process group or owned tree gracefully, wait for a bounded interval, then escalate only within that verified ownership boundary. Verify that the owned children exited. Never infer ownership from an executable name, a PID alone, parentage alone, or resource usage.

For a persistent process, record the handoff and leave it running. For a task process, clean it up on success, failure, cancellation, or loss of safe recovery headroom.
