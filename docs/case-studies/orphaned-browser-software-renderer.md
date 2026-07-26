# Case study: orphaned browser software renderer

## Symptom

An interactive Windows workstation remained above 90% total CPU after an AI
browser-automation task appeared to finish. The visible agent applications
used little CPU, so closing random foreground applications would not have
addressed the cause.

## Evidence chain

Read-only process sampling showed that one Chromium GPU child repeatedly used
roughly 75-87% CPU. Its command context identified:

- a headless browser root with a task-scoped profile and debugging port;
- a forced SwiftShader renderer;
- a detached child whose controller had already exited.

The browser root's start time matched the automation launch record. That
identity evidence made graceful cleanup of that one browser tree safe. No
other browser process was targeted.

## Root cause

Two independent choices combined:

1. `--use-angle=swiftshader` moved WebGL rendering from the available hardware
   GPU to CPU-based software rendering.
2. Detached/unreferenced launch plus a missing browser close allowed the tree
   to outlive its automation task.

An external command timeout bounded the controller, not the detached browser.
When the controller ended, the browser continued rendering without an owner
responsible for cleanup.

## Safe patch pattern

The corrected lifecycle:

1. starts with the browser's normal renderer;
2. retains the launched process or framework browser handle;
3. records PID plus start identity immediately;
4. uses an internal deadline shorter than the external supervisor;
5. closes through the browser framework or CDP in `finally`;
6. verifies that the owned root exited;
7. escalates only through the verified owned group or tree.

It also removes executable-name-wide cleanup. Killing every browser by name
would risk unrelated sessions and would hide the missing-ownership defect.

The runnable
[owned browser lifecycle example](../../examples/owned-browser-lifecycle/)
implements this framework-neutral boundary without a package dependency.

## Verification

A meaningful regression test must exercise process behavior rather than grep
source code. The test should first demonstrate that the old launcher leaves
its child alive. After the fix, it should prove:

- the normal renderer remains active unless a scoped fallback was requested;
- success closes the owned child;
- task failure closes the owned child without hiding the task error;
- the internal deadline closes the owned child;
- unverifiable exit is reported instead of assumed.

After the incident-specific browser was closed, the matching process count
was zero and total CPU returned to normal interactive levels.
