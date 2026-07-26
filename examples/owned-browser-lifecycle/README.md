# Owned browser lifecycle

This dependency-free Node example turns the skill's process-ownership rules
into a reusable control boundary for Playwright, Puppeteer, raw CDP, or another
browser adapter.

It does not launch or terminate a browser by name. The caller supplies a
framework-specific adapter that retains the owned root, closes it gracefully,
and verifies that the same owned process exited.

## Use

```javascript
const { withOwnedBrowser } = require('./with-owned-browser.cjs');

const result = await withOwnedBrowser({
  launch: async (signal) => launchFrameworkBrowser({ signal }),
  run: async (browser, signal) => captureScreenshots(browser, { signal }),
  timeoutMs: 210000,
  cleanupGraceMs: 3000,
  onOwnership: async (record) => writeTaskScopedOwnershipRecord(record),
});
```

`launchFrameworkBrowser` must return:

| Field | Contract |
| --- | --- |
| `browser` | Framework or CDP object passed to `run` |
| `rootPid` | Browser root PID, captured immediately after launch |
| `startIdentity` | OS process creation time or equivalent stable identity |
| `purpose` | Bounded description of this browser task |
| `workingDirectory` | Directory associated with this task |
| `childGroup` | Job Object, process group, retained handle, or explicit unavailable marker |
| `close()` | Framework-native graceful shutdown such as `browser.close()` |
| `waitForExit(ms)` | Returns `true` only when the owned root is verified exited |

Persist the `onOwnership` record beside task logs before doing browser work.
Before any fallback termination, re-read the root and match both PID and
`startIdentity`. A failed match is not owned.

## Deadline ordering

Make the harness deadline shorter than an external supervisor:

```text
internal cleanup deadline: 210 seconds
external command deadline: 220 seconds
```

This gives `finally` time to close and verify the browser before the outer
supervisor can terminate the controller.

## Renderer policy

Start with the normal renderer. Do not add SwiftShader, WARP, llvmpipe,
`--disable-gpu`, or similar flags because a GPU merely exists or a deadline is
close.

Use software rendering only after reproducing a representative failure with
the normal renderer. Scope the fallback to one owned browser, verify the
active renderer, reduce concurrency when needed, and restore the normal
configuration during cleanup.

## Verify

The tests launch real harmless Node child processes; they do not launch a
browser or use the network:

```powershell
node --test examples/owned-browser-lifecycle/with-owned-browser.test.cjs
```

They cover success, task failure, internal timeout, unverifiable cleanup, and
ownership reporting.
