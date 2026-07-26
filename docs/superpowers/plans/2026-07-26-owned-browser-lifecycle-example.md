# Owned Browser Lifecycle Example Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a dependency-free Node lifecycle harness, executable subprocess tests, and an anonymized browser CPU case study.

**Architecture:** A framework-neutral `withOwnedBrowser` function wraps a caller-supplied launch adapter. The adapter returns the browser object plus explicit process identity, graceful cleanup, and exit verification methods; the harness applies the internal deadline and guarantees cleanup on success, failure, or timeout.

**Tech Stack:** CommonJS on Node 18+, Node's built-in test runner, Python repository tests, Markdown, GitHub Actions.

## Global Constraints

- Do not include any private project name, URL, path, session identifier, screenshot, or command history.
- Do not terminate processes by executable name.
- Do not add a package dependency, network call, telemetry, or privilege requirement.
- Keep software-renderer flags out of the example; normal hardware rendering remains the default.
- Keep the existing canonical skill payload and release manifest unchanged.

---

### Task 1: Define the lifecycle contract with failing subprocess tests

**Files:**
- Create: `examples/owned-browser-lifecycle/with-owned-browser.test.cjs`

**Interfaces:**
- Consumes: `withOwnedBrowser`, `BrowserTimeoutError`, and `BrowserCleanupError` from `./with-owned-browser.cjs`.
- Produces: executable behavioral coverage for success, task failure, timeout, cleanup verification, ownership reporting, and stalled reporting.

- [ ] **Step 1: Write the real-process test helper**

Use Node itself as a harmless long-lived child:

```javascript
const { spawn } = require('node:child_process');

function launchChild(overrides = {}) {
  const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], {
    stdio: 'ignore',
  });
  return {
    browser: { pid: child.pid },
    rootPid: child.pid,
    startIdentity: new Date().toISOString(),
    purpose: 'lifecycle regression test',
    workingDirectory: __dirname,
    childGroup: 'retained-child-handle',
    close: async () => child.kill(),
    waitForExit: async (milliseconds) => waitForExit(child, milliseconds),
    ...overrides,
  };
}
```

- [ ] **Step 2: Add six behavior tests**

Implement tests with these literal expectations:

```javascript
test('closes the owned child after a successful task', async () => {
  let rootPid;
  const result = await withOwnedBrowser({
    launch: async () => {
      const record = launchChild();
      rootPid = record.rootPid;
      return record;
    },
    run: async () => 'complete',
    timeoutMs: 1000,
  });
  assert.equal(result, 'complete');
  assert.equal(processExists(rootPid), false);
});

test('closes the owned child and preserves a task failure', async () => {
  let rootPid;
  await assert.rejects(
    withOwnedBrowser({
      launch: async () => {
        const record = launchChild();
        rootPid = record.rootPid;
        return record;
      },
      run: async () => { throw new Error('task failed'); },
      timeoutMs: 1000,
    }),
    /task failed/,
  );
  assert.equal(processExists(rootPid), false);
});

test('closes the owned child at the internal deadline', async () => {
  let rootPid;
  await assert.rejects(
    withOwnedBrowser({
      launch: async () => {
        const record = launchChild();
        rootPid = record.rootPid;
        return record;
      },
      run: async () => new Promise(() => {}),
      timeoutMs: 50,
    }),
    BrowserTimeoutError,
  );
  assert.equal(processExists(rootPid), false);
});
```

Add one cleanup-failure test expecting `BrowserCleanupError`, one ownership
callback test expecting the exact required field names, and one stalled
ownership callback test expecting `BrowserTimeoutError`.

- [ ] **Step 3: Run the test and verify RED**

Run:

```powershell
node --test examples/owned-browser-lifecycle/with-owned-browser.test.cjs
```

Expected: FAIL because `with-owned-browser.cjs` does not exist.

- [ ] **Step 4: Commit the failing contract**

```powershell
git add examples/owned-browser-lifecycle/with-owned-browser.test.cjs
git commit -m "test: define owned browser lifecycle contract"
```

### Task 2: Implement the minimum lifecycle harness

**Files:**
- Create: `examples/owned-browser-lifecycle/with-owned-browser.cjs`
- Test: `examples/owned-browser-lifecycle/with-owned-browser.test.cjs`

**Interfaces:**
- Consumes: caller-supplied `launch`, `run`, and optional `onOwnership` functions.
- Produces: `withOwnedBrowser(options)`, `BrowserTimeoutError`, and `BrowserCleanupError`.

- [ ] **Step 1: Implement errors and ownership validation**

```javascript
class BrowserTimeoutError extends Error {
  constructor(timeoutMs) {
    super(`Owned browser task exceeded ${timeoutMs} ms`);
    this.name = 'BrowserTimeoutError';
  }
}

class BrowserCleanupError extends Error {
  constructor(message, cause) {
    super(message, { cause });
    this.name = 'BrowserCleanupError';
  }
}
```

Require `browser`, a positive integer `rootPid`, non-empty
`startIdentity`, `purpose`, `workingDirectory`, and `childGroup`, plus callable
`close` and `waitForExit`.

- [ ] **Step 2: Implement bounded task execution and cleanup**

```javascript
async function withOwnedBrowser({
  launch,
  run,
  timeoutMs = 210000,
  cleanupGraceMs = 3000,
  onOwnership = async () => {},
}) {
  const controller = new AbortController();
  let record;
  let deadline;
  let primaryError;
  try {
    record = validateRecord(await launch(controller.signal));
    await onOwnership(publicOwnership(record));
    const timeout = new Promise((resolve, reject) => {
      deadline = setTimeout(() => {
        controller.abort();
        reject(new BrowserTimeoutError(timeoutMs));
      }, timeoutMs);
    });
    return await Promise.race([run(record.browser, controller.signal), timeout]);
  } catch (error) {
    primaryError = error;
    throw error;
  } finally {
    clearTimeout(deadline);
    controller.abort();
    const cleanupError = record
      ? await closeAndVerify(record, cleanupGraceMs)
      : null;
    if (cleanupError && primaryError) primaryError.cleanupError = cleanupError;
    else if (cleanupError) throw cleanupError;
  }
}
```

`closeAndVerify` calls `close` once, waits no longer than the cleanup grace,
then requires `waitForExit` to return `true`. It does not invent a fallback
kill command.

- [ ] **Step 3: Run the focused Node tests and verify GREEN**

Run:

```powershell
node --test examples/owned-browser-lifecycle/with-owned-browser.test.cjs
```

Expected: 6 tests pass, 0 fail, and no child process remains.

- [ ] **Step 4: Commit the implementation**

```powershell
git add examples/owned-browser-lifecycle/with-owned-browser.cjs
git commit -m "feat: add owned browser lifecycle harness"
```

### Task 3: Publish usage guidance and case-study evidence

**Files:**
- Create: `examples/owned-browser-lifecycle/README.md`
- Create: `docs/case-studies/orphaned-browser-software-renderer.md`
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the Task 2 harness and its public ownership record.
- Produces: a discoverable adaptation guide, incident evidence, and three-OS CI coverage.

- [ ] **Step 1: Document adapter usage**

The example README must show:

```javascript
const result = await withOwnedBrowser({
  launch: async (signal) => launchFrameworkBrowser({ signal }),
  run: async (browser, signal) => captureScreenshots(browser, { signal }),
  timeoutMs: 210000,
  onOwnership: async (record) => writeTaskScopedOwnershipRecord(record),
});
```

Explain that `launchFrameworkBrowser` must return the complete ownership
record and that framework-native `browser.close()` is the graceful cleanup.
An external supervisor must expire after the internal deadline.

- [ ] **Step 2: Write the anonymized case study**

Describe the observed CPU saturation, identification of a Chromium GPU child,
detached/unreferenced launch, forced SwiftShader, missing browser close, safe
owned cleanup, and renderer/exit verification. Use no incident identifiers.

- [ ] **Step 3: Link the material and run Node tests in CI**

Add a README link near the safety model. Add this CI step after Python tests:

```yaml
- name: Test owned browser lifecycle example
  run: node --test examples/owned-browser-lifecycle/with-owned-browser.test.cjs
```

- [ ] **Step 4: Run privacy and repository verification**

Run:

```powershell
rg -n "AppData\\\\Local\\\\Temp\\\\claude|remote-debugging-port=9333|taskkill /IM|Stop-Process -Name|killall|pkill" examples docs/case-studies
node --test examples/owned-browser-lifecycle/with-owned-browser.test.cjs
python -m compileall skills tests
python -m unittest discover -s tests -v
python tests/validate_skill.py skills/resource-safe-execution
git diff --check
```

Expected: the privacy scan returns no matches; Node and Python suites pass;
the validator exits zero; the diff check is clean.

- [ ] **Step 5: Commit documentation and CI**

```powershell
git add README.md .github/workflows/ci.yml examples docs/case-studies
git commit -m "docs: publish orphaned browser prevention guide"
```

### Task 4: Publish and integrate

**Files:**
- Review: all branch changes against `origin/main`

**Interfaces:**
- Consumes: the verified branch.
- Produces: a focused GitHub pull request and merged public documentation.

- [ ] **Step 1: Review the final branch**

```powershell
git status -sb
git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
```

- [ ] **Step 2: Push the branch**

```powershell
git push -u origin agent/owned-browser-lifecycle
```

- [ ] **Step 3: Open a draft pull request**

The PR title is `Add an owned browser lifecycle example`. Its body covers the
root cause, the generic harness, privacy boundary, developer impact, and exact
verification commands.

- [ ] **Step 4: Inspect CI and merge**

Wait for every required check. Mark the PR ready and merge only when checks
pass and the branch remains mergeable.
