# 38-second demo storyboard

The committed GIF is a deterministic, screen-only
**RECORDED EVALUATION PLAYBACK**. It is not a recording of a proprietary
agent client and it is not a benchmark. The preflight figures are redacted
aggregates from a fresh read-only Windows probe on 2026-07-25; they describe
one moment on one machine and will vary elsewhere.

## 0–4s — Pain

**On screen**

- Request: run eight browser workers, an emulator, and two builds.
- Constraint: keep the interactive workstation responsive.

**Caption:** Agents guess. Your workstation pays.

**Source evidence:** The pressure request is the unchanged scenario in
`docs/evaluations/raw/skill-enabled/concurrency-pressure.md` lines 3–8.

**Boundary:** This scene states the request, not a measured result.

## 4–10s — Read-only preflight

**On screen**

- 12 logical CPUs; sampled CPU 41.7%.
- 18.6 GB of 34.2 GB memory available.
- 28.7 GB disk space free.
- Three graphics devices visible; application backend unverified.

**Caption:** Inspect before launching.

**Source evidence:** The aggregates came from:

```powershell
python skills/resource-safe-execution/scripts/resource_probe.py --format json --sample-seconds 0.5
```

The probe contract is documented in
[`skills/resource-safe-execution/SKILL.md`](../../skills/resource-safe-execution/SKILL.md#1-preflight)
and implemented by
[`resource_probe.py`](../../skills/resource-safe-execution/scripts/resource_probe.py).

**Boundary:** The capture omits its timestamp, host path, device names, driver
versions, and process list. GPU visibility is not application acceleration.

## 10–17s — Bounded plan

**On screen**

- Eight workers were requested.
- Start with one smoke-test worker and measure peak memory.
- Compute `W = min(request, CPU cap, memory cap)`.
- Launch only the measured cap; serialize work when a gate is unknown.

**Caption:** Bound concurrency from current headroom.

**Source evidence:** The gated launch order and worker formula appear in
`docs/evaluations/raw/skill-enabled/concurrency-pressure.md` lines 62–81.
The canonical policy is
[`SKILL.md` section 3](../../skills/resource-safe-execution/SKILL.md#3-choose-a-profile).

**Boundary:** No fixed worker count is claimed. The fresh probe's generic
profile ceiling is not a workload-specific Playwright decision.

## 17–23s — Verify acceleration

**On screen**

1. Detect device.
2. Verify driver/API.
3. Verify the application's backend.
4. Run a representative test.
5. Observe utilization and transfer cost.

**Caption:** Hardware detected ≠ workload accelerated.

**Source evidence:** The five-level ladder is
[`skills/resource-safe-execution/references/gpu-selection.md`](../../skills/resource-safe-execution/references/gpu-selection.md#gpu-selection).
The historical GPU evaluation is summarized in
`docs/evaluations/2026-07-24-skill-enabled.md` lines 53–64.

**Boundary:** Device detection alone proves neither backend selection nor a
performance gain.

## 23–31s — Track ownership

**On screen**

- Record root PID plus platform start identity immediately after launch.
- Retain the task's process-group, Job Object, container, or launcher handle.
- Refuse executable-name-wide cleanup.

**Caption:** Track what the agent starts.

**Source evidence:** The ownership record and identity check are defined in
[`skills/resource-safe-execution/references/process-lifecycle.md`](../../skills/resource-safe-execution/references/process-lifecycle.md#process-lifecycle).
The evaluated refusal is recorded in
`docs/evaluations/2026-07-24-skill-enabled.md` lines 40–51.

**Boundary:** The visual uses placeholders, not a real PID or command line.

## 31–36s — Cleanup

**On screen**

1. Re-read PID and start identity.
2. Request the recorded graceful stop.
3. Escalate only inside the verified owned group.
4. Verify exit.

**Caption:** Clean up only owned work.

**Source evidence:** The safe cleanup sequence appears in
[`process-lifecycle.md`](../../skills/resource-safe-execution/references/process-lifecycle.md#process-lifecycle)
and `docs/evaluations/raw/skill-enabled/concurrency-pressure.md` lines 97–105.

**Boundary:** Missing or mismatched ownership evidence requires refusal.

## 36–38s — CTA

**On screen**

```text
npx --yes skills@1.5.20 add pntech20/resource-safe-execution --skill resource-safe-execution --copy
```

**Caption:** Skill runtime: no network or telemetry. Third-party `skills CLI`:
anonymous, opt-out install telemetry.

**Source evidence:** The command and telemetry boundary are documented in the
repository [README](../../README.md#fast-install).

## Evaluation provenance

The historical scorecard reports all 17 unchanged required signals present.
It also explicitly says those responses are historical evidence, not an
evaluation of the current `SKILL.md`; see
`docs/evaluations/2026-07-24-skill-enabled.md` lines 5–9 and 81–83.

## Pre-capture and release checklist

1. Re-run the read-only probe and copy only aggregate values approved above.
2. Close unrelated apps; hide notifications, tabs, clock, and account UI.
3. Remove usernames, host paths, tokens, commands, environment variables,
   device names, driver versions, and unrelated process names.
4. Confirm the playback label, evidence boundaries, and exact install command.
5. Inspect the loop at original size and at a 360 px viewport; reject clipping
   or text that cannot be read.
