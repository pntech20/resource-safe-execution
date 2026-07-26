'use strict';

class BrowserTimeoutError extends Error {
  constructor(timeoutMs) {
    super(`Owned browser task exceeded ${timeoutMs} ms`);
    this.name = 'BrowserTimeoutError';
  }
}

class BrowserCleanupError extends Error {
  constructor(message, cause) {
    super(message, cause === undefined ? undefined : { cause });
    this.name = 'BrowserCleanupError';
  }
}

function requireFunction(value, name) {
  if (typeof value !== 'function') {
    throw new TypeError(`${name} must be a function`);
  }
}

function requirePositiveInteger(value, name) {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new TypeError(`${name} must be a positive integer`);
  }
}

function requireText(value, name) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new TypeError(`${name} must be a non-empty string`);
  }
}

function validateRecord(record) {
  if (!record || typeof record !== 'object') {
    throw new TypeError('launch must return an ownership record');
  }
  if (!Object.prototype.hasOwnProperty.call(record, 'browser')) {
    throw new TypeError('ownership record must include browser');
  }
  requirePositiveInteger(record.rootPid, 'rootPid');
  requireText(record.startIdentity, 'startIdentity');
  requireText(record.purpose, 'purpose');
  requireText(record.workingDirectory, 'workingDirectory');
  requireText(record.childGroup, 'childGroup');
  requireFunction(record.close, 'close');
  requireFunction(record.waitForExit, 'waitForExit');
  return record;
}

function publicOwnership(record) {
  return Object.freeze({
    rootPid: record.rootPid,
    startIdentity: record.startIdentity,
    purpose: record.purpose,
    workingDirectory: record.workingDirectory,
    expectedLifetime: 'task',
    cleanupMethod: 'adapter close() then waitForExit()',
    childGroup: record.childGroup,
  });
}

function within(promise, milliseconds, timeoutMessage) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new BrowserCleanupError(timeoutMessage)),
      milliseconds,
    );
    Promise.resolve(promise).then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}

async function closeAndVerify(record, cleanupGraceMs) {
  const cleanupDeadline = Date.now() + cleanupGraceMs;
  try {
    await within(
      Promise.resolve().then(() => record.close()),
      cleanupGraceMs,
      `Owned browser ${record.rootPid} did not close within ${cleanupGraceMs} ms`,
    );
    const remaining = Math.max(1, cleanupDeadline - Date.now());
    const exited = await within(
      Promise.resolve().then(() => record.waitForExit(remaining)),
      remaining,
      `Owned browser ${record.rootPid} exit verification timed out`,
    );
    if (exited !== true) {
      return new BrowserCleanupError(
        `Owned browser ${record.rootPid} exit could not be verified`,
      );
    }
    return null;
  } catch (error) {
    if (error instanceof BrowserCleanupError) return error;
    return new BrowserCleanupError(
      `Owned browser ${record.rootPid} cleanup failed`,
      error,
    );
  }
}

async function withOwnedBrowser({
  launch,
  run,
  timeoutMs = 210000,
  cleanupGraceMs = 3000,
  onOwnership = async () => {},
}) {
  requireFunction(launch, 'launch');
  requireFunction(run, 'run');
  requireFunction(onOwnership, 'onOwnership');
  requirePositiveInteger(timeoutMs, 'timeoutMs');
  requirePositiveInteger(cleanupGraceMs, 'cleanupGraceMs');

  const controller = new AbortController();
  let record;
  let deadline;
  let primaryError;

  try {
    record = validateRecord(await launch(controller.signal));
    const timeout = new Promise((resolve, reject) => {
      deadline = setTimeout(() => {
        controller.abort();
        reject(new BrowserTimeoutError(timeoutMs));
      }, timeoutMs);
    });
    await Promise.race([
      Promise.resolve().then(() => onOwnership(publicOwnership(record))),
      timeout,
    ]);
    return await Promise.race([
      Promise.resolve().then(() => run(record.browser, controller.signal)),
      timeout,
    ]);
  } catch (error) {
    primaryError = error;
    throw error;
  } finally {
    clearTimeout(deadline);
    controller.abort();
    const cleanupError = record
      ? await closeAndVerify(record, cleanupGraceMs)
      : null;
    if (cleanupError && primaryError) {
      primaryError.cleanupError = cleanupError;
    } else if (cleanupError) {
      throw cleanupError;
    }
  }
}

module.exports = {
  BrowserCleanupError,
  BrowserTimeoutError,
  withOwnedBrowser,
};
