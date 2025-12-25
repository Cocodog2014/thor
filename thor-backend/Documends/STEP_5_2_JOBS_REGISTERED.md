# Step 5.2 - Add Jobs to Registry ✅ COMPLETE

## Summary
All 8 jobs have been successfully added to the heartbeat registry and are ready to execute.

## Jobs Registered (8 total)

| Job Class | File | Interval | Purpose |
|-----------|------|----------|---------|
| IntradayJob | intraday_job.py | 1.0s | Process market ticks, update intraday metrics |
| Week52ExtremesJob | week52_extremes_job.py | 2.0s | Update 52-week rolling statistics |
| SessionVolumeJob | session_volume_job.py | 10.0s | Accumulate session volume metrics |
| MarketMetricsJob | market_metrics_job.py | 10.0s | Update market metrics from quotes |
| TwentyFourHourJob | twentyfour_hour_job.py | 30.0s | Update 24-hour rolling data |
| PreOpenBacktestJob | preopen_backtest_job.py | 30.0s | Run backtests 1-60s before market open |
| VwapMinuteCaptureJob | vwap_minute_capture_job.py | 60.0s | Capture minute-level VWAP snapshots |
| ClosedBarsFlushJob | closed_bars_flush_job.py | 60.0s | Flush closed price bars (only when markets open) |

## Registration Location

**File**: `ThorTrading/services/supervisors/register_jobs.py`

The `register_all_jobs(registry: JobRegistry) -> int` function:
- ✅ Imports all 8 Job classes
- ✅ Registers each with appropriate interval_seconds
- ✅ Returns count of registered jobs (8)
- ✅ Centralized location (single source of truth)

## Heartbeat Command Integration

**File**: `GlobalMarkets/management/commands/run_heartbeat.py`

The command:
1. Creates JobRegistry instance
2. Calls `register_all_jobs(registry)` to populate it
3. Logs: "Heartbeat ready with 8 jobs"
4. Runs heartbeat loop that executes jobs on schedule

## Usage

```bash
python manage.py run_heartbeat [--fast-tick 1.0] [--slow-tick 60.0] [--no-lock]
```

**Output**:
```
🚀 Heartbeat scheduler starting
   Fast tick: 1.0s (markets open)
   Slow tick: 60.0s (markets closed)
   Leader lock: enabled
✓ Leader lock acquired
Heartbeat ready with 8 jobs
💓 Heartbeat started with tick=1.0s; jobs_due=[IntradayJob, Week52ExtremesJob, ...]
...
```

## Execution Order (by interval)

Every tick, jobs are checked in this order:

1. **1.0s** - IntradayJob (1/1 ticks)
2. **2.0s** - Week52ExtremesJob (1/2 ticks)
3. **10.0s** - SessionVolumeJob, MarketMetricsJob (1/10 ticks)
4. **30.0s** - TwentyFourHourJob, PreOpenBacktestJob (1/30 ticks)
5. **60.0s** - VwapMinuteCaptureJob, ClosedBarsFlushJob (1/60 ticks)

## Implementation Details

### Job Protocol
All jobs implement the `Job` protocol from `core.infra.jobs`:

```python
class Job(Protocol):
    name: str
    interval_seconds: float
    
    def run(self, context: HeartbeatContext) -> None:
        """Execute the job."""
    
    def should_run(self, now: float, state: Dict[str, float]) -> bool:
        """Check if interval has elapsed since last run."""
```

### Registry Tracking
JobRegistry maintains a shared state dict:
```python
state = {
    "IntradayJob": last_run_time,
    "Week52ExtremesJob": last_run_time,
    ...
}
```

Each job's `should_run()` checks:
- If `now - state[job_name] >= job.interval_seconds`
- If True, updates `state[job_name] = now`
- Returns True (job will execute)

## Verification

To verify all jobs are registered:

```bash
cd A:\Thor\thor-backend

# Start heartbeat in debug mode
python manage.py run_heartbeat --no-lock

# Check logs for:
# "Heartbeat ready with 8 jobs"
# "jobs_due=[...all 8 jobs...]"
```

## Next Steps

Jobs are now ready to:
1. ✅ Register with heartbeat (DONE)
2. ⏳ Execute on schedule (when `run_heartbeat` command starts)
3. ⏳ Coordinate via Redis state (when in multi-worker deployment)
4. ⏳ Handle market open/close transitions (via has_active_markets())

---

**Status**: ✅ COMPLETE  
**Date**: 2025-12-19  
**Jobs Registered**: 8/8  
**Entry Point**: `python manage.py run_heartbeat`

