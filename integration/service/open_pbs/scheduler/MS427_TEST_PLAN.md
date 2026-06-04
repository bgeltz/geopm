# MS 427 Test Plan — PBS Scheduling with GEOPM Power Hooks

## Overview

We evaluate the job scheduling effects of the GEOPM PBS hooks on Sunspot using
OpenPBS. The hooks assign `geopm-job-power-limit` as a consumable resource so
that the PBS scheduler gates job admission based on a cluster-wide power budget.

We use `qstat -f -x` to evaluate which job resources were assigned by the
GEOPM PBS hooks. The following bash function simplifies extraction of the
assigned power per job:

```bash
# Usage: show_geopm_job <pbs_job_id>
show_geopm_job() { qstat -f -x "$1" 2>/dev/null | awk '/Resource_List\.geopm/ { sub(/.*Resource_List\./, ""); gsub(/ = /, "="); print }'; }
```

Job execution is monitored with `qstat`. Each `qsub` command prints a job ID
which is used as input to `show_geopm_job` to view the assigned power.

## Environment

- **System**: Sunspot, 2 dedicated test nodes (isolated queue)
- **PBS**: OpenPBS on Sunspot
- **Account/Queue**: `-A Intel-punchlist -q geopm-test`
- **GEOPM power resources**:
  - `geopm-min-node-power-limit` = 2400 (W)
  - `geopm-max-node-power-limit` = 4000 (W)
  - `geopm-job-power-limit` = cluster cap (consumable, flag=q)

## Roles and Workflow

Testing requires coordination between a **PBS admin** and a **tester** (unprivileged user).

### Admin role (`admin_setup.sh`)

1. **One-time queue creation**: Create a dedicated 2-node execution queue
   (`geopm-test`) to isolate tests from production workq jobs:
   ```bash
   ./admin_setup.sh create-queue <node1> <node2>
   ```
   This assigns 2 specific nodes to the test queue. Those nodes will not run
   workq jobs during testing.

2. **Per-phase resource setup**: Set the queue-level cluster cap for each
   test phase. The admin runs one phase command, signals the tester, then
   moves to the next after the tester finishes:
   ```bash
   ./admin_setup.sh phase1   # cap=100000 (TC1, TC3, TC4)
   ./admin_setup.sh phase2   # cap=8000  (TC6)
   ./admin_setup.sh phase3   # cap=6000  (TC2, TC7)
   ./admin_setup.sh phase4   # cap=4000  (TC5)
   ```
   Resources are set at the **queue level** only — jobs in other queues
   (e.g., `workq`) are completely unaffected.

3. **Teardown**: After all tests, remove the queue and unset resources:
   ```bash
   ./admin_setup.sh teardown
   ```

> **Note:** The GEOPM server hook has been updated to check queue-level
> `resources_available` first, falling back to server-level. This means power
> resources set on the test queue do NOT affect jobs in other queues.

### Tester role (`test_scheduling.sh`)

The tester runs the matching test phase after the admin signals readiness:
```bash
export GEOPM_TEST_QUEUE=geopm-test   # or whatever the admin named it
./test_scheduling.sh phase1           # after admin runs admin_setup.sh phase1
./test_scheduling.sh phase2           # after admin runs admin_setup.sh phase2
./test_scheduling.sh phase3           # after admin runs admin_setup.sh phase3
./test_scheduling.sh phase4           # after admin runs admin_setup.sh phase4
```

### Phase grouping (fewest admin changes)

| Phase | Cluster cap | Test cases | What it validates |
|-------|-------------|------------|-------------------|
| 1     | 100000 W    | TC1, TC3, TC4 | Jobs run at full power; cap not binding |
| 2     | 8000 W      | TC6        | Backfill works with adequate power headroom |
| 3     | 6000 W      | TC2, TC7   | Moderate cap serializes 2-node jobs; user power cap enables backfill |
| 4     | 4000 W      | TC5        | Tight cap serializes even 1-node jobs |

Each test case contains a **description** of the test itself and **expected
outcomes** from running the test. The admin setup for each phase is handled
separately via `admin_setup.sh`.

> **Note:** On Sunspot, jobs typically take 30–60 seconds from `qsub` to
> Running state. The test scripts account for this with a polling loop
> (`wait_job_running`) that waits up to `STARTUP_TIMEOUT` (default: 120s)
> before evaluating scheduling behavior. `JOB_SLEEP` is set to 120s to
> ensure jobs remain in Running state long enough to observe concurrency.

---

## TC1. Jobs Execute Immediately Under No Power or Node Contention

**Phase:** 1 (cap=100000)

**Description:**

```bash
qsub -A Intel-punchlist -q geopm-test -I -koed -joe \
    -l filesystems=home -l walltime=00:10:00 \
    -l "select=2" \
    -- /usr/bin/sh -c 'echo Hey $(hostname)'
```

**Expected outcome:** `qsub` succeeds immediately (job starts without delay).
No power-related gating occurs because the default slowdown of 0.0 results in
full power assignment and the cluster cap has headroom.

---

## TC2. Default Job Power Limits are Limited by the System Budget

The cluster cap is set lower than what `max_node × nodes` would allow, so the
hook clamps each job's power to the system budget.

**Phase:** 3 (cap=6000)

**Description:**

```bash
for i in {1..2}; do
    qsub -A Intel-punchlist -q geopm-test -koed -joe \
        -l filesystems=home -l walltime=00:10:00 \
        -l "select=2" \
        -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'
done

qstat && sleep 10 && qstat && sleep 30 && qstat && sleep 10 && qstat
```

**Expected outcome:** Both jobs are in the queue, then just one job runs at a
time, then no jobs remain. Each job is assigned 6000 W per job (the max node
limit would allow 8000 W = 2 × 4000, but the system-wide job limit caps it
at 6000 W). The second job cannot start until the first finishes because
6000 + 6000 > 6000.

**Verification:**

```bash
show_geopm_job <job1_id>  # expect geopm-job-power-limit=6000
show_geopm_job <job2_id>  # expect geopm-job-power-limit=6000
```

---

## TC3. Default Job Power Caps are Limited by the Max Node Power

The cluster cap is set high enough that it does not constrain; the per-node max
becomes the binding limit.

**Phase:** 1 (cap=100000)

**Description:**

```bash
for i in {1..2}; do
    qsub -A Intel-punchlist -q geopm-test -koed -joe \
        -l filesystems=home -l walltime=00:10:00 \
        -l "select=2" \
        -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'
done

qstat && sleep 10 && qstat && sleep 30 && qstat && sleep 10 && qstat
```

**Expected outcome:** Both jobs run concurrently (the cluster cap is large
enough for both). Each job is assigned 8000 W (2 nodes × 4000 W max per node).

**Verification:**

```bash
show_geopm_job <job1_id>  # expect geopm-job-power-limit=8000
show_geopm_job <job2_id>  # expect geopm-job-power-limit=8000
```

---

## TC4. Single-node Jobs Run Concurrently When There is Enough Power

**Phase:** 1 (cap=100000)

**Description:**

```bash
for i in {1..2}; do
    qsub -A Intel-punchlist -q geopm-test -koed -joe \
        -l filesystems=home -l walltime=00:10:00 \
        -l "select=1" \
        -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'
done

qstat && sleep 10 && qstat && sleep 30 && qstat && sleep 10 && qstat
```

**Expected outcome:** Both single-node jobs run at the same time (cluster cap
has plenty of headroom for 2 × 4000 W). Each job is assigned 4000 W.

---

## TC5. Single-node Jobs Run in Series When There is Not Enough Power

**Phase:** 4 (cap=4000)

**Description:**

```bash
for i in {1..2}; do
    qsub -A Intel-punchlist -q geopm-test -koed -joe \
        -l filesystems=home -l walltime=00:10:00 \
        -l "select=1" \
        -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'
done

qstat && sleep 10 && qstat && sleep 30 && qstat && sleep 10 && qstat
```

**Expected outcome:** Both jobs are queued but only one runs at a time. The
cluster cap (4000 W) fits exactly one 4000 W single-node job. The second job
starts only after the first finishes.

---

## TC6. Backfiller is Not Disrupted by Automatic Power Cap Selection

**Phase:** 2 (cap=8000). Also requires `strict_ordering` in the scheduler config.

**Description:**

```bash
# Job 1: Starts ASAP. Uses 1 node (creates a scheduler hole).
qsub -A Intel-punchlist -q geopm-test -koed -joe \
    -l filesystems=home -l walltime=5:00 \
    -l "select=1" \
    -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 120'

# Job 2: High-priority 2-node job. Top job behind Job 1.
qsub -A Intel-punchlist -q geopm-test -koed -joe -p1000 \
    -l filesystems=home -l walltime=1:00 \
    -l "select=2" \
    -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'

# Job 3: Low-priority 1-node job. Backfill candidate by node count,
# but rejected due to walltime (won't finish before Job 2 needs resources).
qsub -A Intel-punchlist -q geopm-test -koed -joe -p0 \
    -l filesystems=home -l walltime=5:30 \
    -l "select=1" \
    -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'

# Job 4: Low-priority 1-node job with short walltime. Backfill lets it
# start early since it will finish before Job 2's estimated start.
qsub -A Intel-punchlist -q geopm-test -koed -joe -p0 \
    -l filesystems=home -l walltime=1:00 \
    -l "select=1" \
    -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'

qstat && sleep 60 && qstat && sleep 30 && qstat && sleep 30 && qstat
```

**Expected outcome:** Jobs 1 and 4 run immediately (Job 4 backfills into the
hole). Then Job 2 runs after Job 1 finishes. Then Job 3. Each single-node job
is assigned 4000 W. The two-node job is assigned 8000 W.

---

## TC7. Backfiller Respects System Power Limits

Same as TC6 but with a tighter power cap that prevents backfill unless the job
requests less power.

**Phase:** 3 (cap=6000). Also requires `strict_ordering` in the scheduler config.

**Description:**

```bash
# Job 1: Starts ASAP. 1-node job (4000 W assigned).
qsub -A Intel-punchlist -q geopm-test -koed -joe \
    -l filesystems=home -l walltime=5:00 \
    -l "select=1" \
    -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 120'

# Job 2: High-priority 2-node job. Would need 8000 W but cap is 6000 W,
# so it gets clamped to 6000 W. Cannot co-run with Job 1 (4000+6000 > 6000).
qsub -A Intel-punchlist -q geopm-test -koed -joe -p1000 \
    -l filesystems=home -l walltime=1:00 \
    -l "select=2" \
    -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'

# Job 3: Low-priority 1-node job. Would get 4000 W. Cannot backfill
# because 4000 + 4000 (Job 1) > 6000 (cap). Stays queued.
qsub -A Intel-punchlist -q geopm-test -koed -joe -p0 \
    -l filesystems=home -l walltime=1:00 \
    -l "select=1" \
    -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'

# Job 4: Low-priority 1-node job with explicit low power cap.
# User requests only 2000 W. Can backfill because 4000 + 2000 ≤ 6000.
qsub -A Intel-punchlist -q geopm-test -koed -joe -p0 \
    -l filesystems=home -l walltime=1:00 \
    -l "select=1" -l geopm-job-power-limit=2000 \
    -- /usr/bin/sh -c 'echo Hey $(hostname) && sleep 30'

qstat && sleep 60 && qstat && sleep 30 && qstat && sleep 30 && qstat
```

**Expected outcome:** Jobs 1 and 4 run immediately (Job 4 fits under the
remaining power budget: 6000 − 4000 = 2000 ≥ 2000). Then Job 2 runs after
Job 1 finishes. Then Job 3. Job 1 gets 4000 W, Job 2 gets 6000 W (clamped),
Job 3 gets 4000 W, Job 4 gets the user-requested 2000 W.

---

## Execution Notes

1. Admin creates the test queue once, then cycles through phases 1–4.
2. Tester runs the matching `./test_scheduling.sh phaseN` after each admin setup.
3. Total test time: ~15 minutes (4 phase changes + job execution).
4. TC6/TC7 require `strict_ordering` in the scheduler config — the admin
   should verify/enable this before phase 2.
5. Between phases, ensure no leftover test jobs: `qstat | grep ms427` should be empty.
6. Use `show_geopm_job` after each test to record assigned power values.
7. Sleep times may need adjustment based on Sunspot job startup latency
   (typically 10–30s for small jobs). Set `JOB_SLEEP` and `POLL_INTERVAL`
   environment variables to tune.
8. After all testing, admin runs `./admin_setup.sh teardown` to restore
   the 2 nodes to production.
