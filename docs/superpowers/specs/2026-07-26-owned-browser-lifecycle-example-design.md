# Owned Browser Lifecycle Example: Design Specification

Status: approved for implementation

Date: 2026-07-26

Repository: `pntech20/resource-safe-execution`

## 1. Purpose

Publish a sanitized, reusable version of a real browser-automation failure:
an agent launched a detached Chromium process, forced software rendering, and
exited without closing the browser tree. The abandoned GPU process consumed
most of the host CPU until it was identified and closed.

The public material must help developers prevent the pattern without exposing
project names, URLs, local paths, session identifiers, screenshots, or other
incident-specific data.

## 2. Selected approach

Ship a dependency-free CommonJS lifecycle harness, executable Node tests, and
an anonymized case study.

The harness will wrap a caller-supplied browser adapter instead of embedding a
specific browser framework. This keeps it useful with Playwright, Puppeteer,
raw CDP, and agent-specific browser tools while preserving one ownership
contract:

```text
launch adapter -> ownership record -> bounded task -> close -> verify exit
```

The repository will not publish the temporary incident script. It will not
add a general-purpose process killer or infer ownership from executable names.

## 3. Public interfaces

`withOwnedBrowser(options)` will accept:

- `launch(signal)`: returns an ownership record;
- `run(browser, signal)`: performs the bounded browser task;
- `timeoutMs`: an internal deadline shorter than any external supervisor;
- `cleanupGraceMs`: the maximum wait for verified shutdown;
- `onOwnership(record)`: an optional callback that persists or logs ownership.

The launch result must contain:

- `browser`: the framework or CDP object used by the task;
- `rootPid`: the browser root PID;
- `startIdentity`: process creation time or an equivalent stable identity;
- `purpose`: a bounded task description;
- `workingDirectory`: the task directory;
- `childGroup`: a process-group, Job Object, or explicit unavailable marker;
- `close()`: graceful browser shutdown;
- `waitForExit(milliseconds)`: verifies the owned root exited.

The harness will return the task result on success. It will throw a timeout
error when its internal deadline expires and a cleanup error when the adapter
cannot prove that the owned browser exited. Cleanup will be idempotent and
will run after success, task failure, or timeout.

## 4. Renderer policy

The example will launch with the browser's normal renderer. It will not
include SwiftShader, WARP, llvmpipe, `--disable-gpu`, or equivalent fallback
flags.

Documentation will state that software rendering is opt-in only after a
representative hardware-rendering failure has been reproduced. The fallback
must be scoped to one owned task, verified through the active renderer, and
restored during cleanup.

## 5. Testing

Node's built-in test runner will exercise real subprocess behavior with a
harmless child process:

1. a successful task closes its child;
2. a failed task closes its child and preserves the task error;
3. an internal deadline closes its child and returns the timeout error;
4. a cleanup that cannot verify exit returns a cleanup error;
5. the ownership callback receives the required identity fields.
6. a stalled ownership callback reaches the same deadline and closes its child.

The tests will not launch a browser, use the network, install packages, or
terminate processes by executable name. CI will run the Node tests on the
existing Windows, macOS, and Linux matrix.

## 6. Documentation

The case study will present:

- the observable symptom;
- the evidence chain from high CPU to the owned root;
- the two-part root cause: forced software rendering and lost lifecycle
  ownership;
- the safe patch pattern;
- red/green verification expectations.

The README will link the case study and runnable example near the safety
model. The canonical skill remains unchanged because its current renderer,
ownership, and cleanup rules already express the required policy; this change
adds an implementation example and incident-derived evidence.

## 7. Acceptance criteria

The change is ready when:

1. every Node lifecycle test passes locally and in the three-OS CI matrix;
2. the existing Python suite and skill validator remain green;
3. no public file contains incident-specific identifiers or broad kill-by-name
   commands;
4. the example has no runtime dependency beyond Node;
5. the pull request explains the root cause, developer impact, and checks.
