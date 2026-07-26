'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');

const {
  BrowserCleanupError,
  BrowserTimeoutError,
  withOwnedBrowser,
} = require('./with-owned-browser.cjs');

const delay = (milliseconds) => new Promise((resolve) => {
  setTimeout(resolve, milliseconds);
});

function processExists(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code === 'EPERM';
  }
}

function waitForExit(child, milliseconds) {
  if (child.exitCode !== null || child.signalCode !== null) {
    return Promise.resolve(true);
  }
  return Promise.race([
    new Promise((resolve) => child.once('exit', () => resolve(true))),
    delay(milliseconds).then(() => false),
  ]);
}

function launchChild(t, overrides = {}) {
  const child = spawn(
    process.execPath,
    ['-e', 'setInterval(() => {}, 1000)'],
    { stdio: 'ignore' },
  );
  t.after(async () => {
    if (processExists(child.pid)) {
      child.kill();
      await waitForExit(child, 1000);
    }
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

test('closes the owned child after a successful task', async (t) => {
  let rootPid;
  const result = await withOwnedBrowser({
    launch: async () => {
      const record = launchChild(t);
      rootPid = record.rootPid;
      return record;
    },
    run: async () => 'complete',
    timeoutMs: 1000,
  });

  assert.equal(result, 'complete');
  assert.equal(processExists(rootPid), false);
});

test('closes the owned child and preserves a task failure', async (t) => {
  let rootPid;
  await assert.rejects(
    withOwnedBrowser({
      launch: async () => {
        const record = launchChild(t);
        rootPid = record.rootPid;
        return record;
      },
      run: async () => {
        throw new Error('task failed');
      },
      timeoutMs: 1000,
    }),
    /task failed/,
  );

  assert.equal(processExists(rootPid), false);
});

test('closes the owned child at the internal deadline', async (t) => {
  let rootPid;
  await assert.rejects(
    withOwnedBrowser({
      launch: async () => {
        const record = launchChild(t);
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

test('reports cleanup failure when owned exit cannot be verified', async (t) => {
  await assert.rejects(
    withOwnedBrowser({
      launch: async () => launchChild(t, {
        close: async () => {},
        waitForExit: async () => false,
      }),
      run: async () => 'complete',
      timeoutMs: 1000,
      cleanupGraceMs: 50,
    }),
    BrowserCleanupError,
  );
});

test('reports the complete ownership record immediately after launch', async (t) => {
  let ownership;
  await withOwnedBrowser({
    launch: async () => launchChild(t),
    run: async () => 'complete',
    timeoutMs: 1000,
    onOwnership: async (record) => {
      ownership = record;
    },
  });

  assert.deepEqual(
    Object.keys(ownership).sort(),
    [
      'childGroup',
      'cleanupMethod',
      'expectedLifetime',
      'purpose',
      'rootPid',
      'startIdentity',
      'workingDirectory',
    ],
  );
  assert.equal(ownership.expectedLifetime, 'task');
  assert.equal(ownership.cleanupMethod, 'adapter close() then waitForExit()');
});

test('closes the owned child when ownership reporting exceeds the deadline', async (t) => {
  let rootPid;
  await assert.rejects(
    withOwnedBrowser({
      launch: async () => {
        const record = launchChild(t);
        rootPid = record.rootPid;
        return record;
      },
      run: async () => 'complete',
      timeoutMs: 50,
      onOwnership: async () => delay(100),
    }),
    BrowserTimeoutError,
  );

  assert.equal(processExists(rootPid), false);
});
