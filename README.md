# Overtime Management for HRMS v15

A Frappe/HRMS v15 app that **automatically calculates overtime hours** from Employee Checkin records. Supports overnight shifts, Ramadan schedules with religion-based rules, configurable rounding, rate multipliers, and an approval workflow.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Overtime Settings](#overtime-settings)
  - [Overtime Shift Rules](#overtime-shift-rules)
  - [Custom Fields](#custom-fields)
- [How It Works](#how-it-works)
  - [Calculation Flow](#calculation-flow)
  - [Overnight Shift Handling](#overnight-shift-handling)
  - [Ramadan Mode](#ramadan-mode)
  - [Shift Rule Matching (Scoring)](#shift-rule-matching-scoring)
- [Shift Schedule Reference](#shift-schedule-reference)
- [API Reference](#api-reference)
- [DocTypes](#doctypes)
- [Extending / Customization](#extending--customization)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

| Feature | Description |
|---|---|
| **Auto-calculation** | Overtime calculated on Attendance submit via `doc_events` hook |
| **Overnight shifts** | Full support for shifts crossing midnight (e.g. 23:30 → 07:30) |
| **Ramadan mode** | Date-range activation with religion-based shift schedules |
| **Shift rule scoring** | Weighted matching: period → religion category → shift type → department |
| **Food/Suhoor breaks** | Configurable break deductions per shift rule |
| **Grace period** | Late arrival / early departure tolerance (per shift rule) |
| **Rounding** | Round Up, Round Down, or Round to Nearest (configurable interval) |
| **Rate multipliers** | Separate rates for normal days vs holidays |
| **Min/Max caps** | Minimum minutes threshold, maximum hours per day |
| **Approval workflow** | Optional manager approval before overtime is finalized |
| **Bulk operations** | Recalculate / bulk-submit overtime via API |
| **Daily scheduler** | Fallback daily job to catch missed attendance events |
| **Attendance sync** | Overtime hours and entry link written back to Attendance record |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Employee Checkin                                   │
│  (IN @ 07:25, OUT @ 16:45)                          │
└───────────────┬─────────────────────────────────────┘
                │  HRMS auto-attendance
                ▼
┌─────────────────────────────────────────────────────┐
│  Attendance (submitted)                             │
│  working_hours = 9.33, shift = Morning              │
└───────────────┬─────────────────────────────────────┘
                │  doc_events → on_submit hook
                ▼
┌─────────────────────────────────────────────────────┐
│  Overtime App (utils.py)                            │
│  1. Load Overtime Settings                          │
│  2. Match best Overtime Shift Rule (scoring)        │
│  3. Get checkin logs for that attendance             │
│  4. Compute actual vs scheduled hours               │
│  5. Deduct food breaks + apply grace                │
│  6. Apply rounding, min/max caps                    │
│  7. Apply rate multiplier (normal/holiday)          │
└───────────────┬─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────┐
│  Overtime Entry (Draft or Submitted)                │
│  overtime_hours = 1.25                              │
│  rate_multiplier = 1.5                              │
│  payable_overtime_hours = 1.875                     │
│  status = Draft → Approved → Submitted             │
└───────────────┬─────────────────────────────────────┘
                │  on_submit
                ▼
┌─────────────────────────────────────────────────────┐
│  Attendance record updated                          │
│  overtime_hours = 1.25                       │
│  overtime_entry = OT-HR-EMP-0001-0001        │
└─────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Frappe v15
- HRMS v15 (installed and configured with Shift Types and Employee Checkin)
- Python 3.10+

### Install

```bash
cd $PATH_TO_YOUR_BENCH

# Get the app
bench get-app $URL_OF_THIS_REPO --branch develop

# Install on your site
bench --site your-site.local install-app overtime

# Run migrations
bench --site your-site.local migrate
```

The `after_install` hook automatically:
1. Creates custom fields on Employee and Attendance
2. Creates default Overtime Settings
3. Creates 7 default Overtime Shift Rules

---

## Configuration

### Overtime Settings

Navigate to **Overtime Settings** (single DocType) to configure global behavior.

| Field | Type | Description |
|---|---|---|
| `enabled` | Check | Master switch — disables all overtime processing when off |
| `overtime_based_on` | Select | `Shift Hours` (scheduled vs actual) or `Fixed Hours` (fixed daily threshold) |
| `minimum_overtime_minutes` | Int | Minimum minutes before overtime counts (e.g. 15 = ignore <15min) |
| `max_overtime_hours_per_day` | Float | Daily cap (e.g. 4.0) |
| `overtime_rounding` | Select | `No Rounding`, `Round Up`, `Round Down`, `Round to Nearest` |
| `rounding_interval_minutes` | Int | Interval for rounding (e.g. 15 = round to 15-min blocks) |
| `default_overtime_rate_multiplier` | Float | Normal-day rate (e.g. 1.5x) |
| `holiday_overtime_rate_multiplier` | Float | Holiday rate (e.g. 2.0x) |
| `require_approval` | Check | If enabled, entries are created as Draft for manager approval |
| `auto_create_overtime_entry` | Check | Auto-create Overtime Entry on Attendance submit |
| `ramadan_mode_enabled` | Check | Enable Ramadan period shift rules |
| `ramadan_start_date` | Date | Ramadan period start |
| `ramadan_end_date` | Date | Ramadan period end |

### Overtime Shift Rules

Navigate to **Overtime Shift Rule** list to manage shift definitions.

Each rule defines:

| Field | Description |
|---|---|
| `shift_name` | Display name (e.g. "Morning", "Night") |
| `applicable_period` | `Standard` or `Ramadan` |
| `employee_category` | `All`, `Muslim`, or `Non-Muslim` |
| `check_in_time` / `check_out_time` | Scheduled shift start/end times |
| `is_overnight_shift` | Check if shift crosses midnight |
| `allow_late_early_exception` | Enable grace period |
| `late_early_grace_minutes` | Grace minutes for late arrival / early departure |
| `has_food_break` | Deduct a food/suhoor break from working hours |
| `food_break_duration_minutes` | Break length in minutes |
| `food_break_type` | `Regular Break` or `Suhoor Break` |
| `food_break_included_in_shift` | If checked, break is deducted from scheduled hours |
| `shift_type` | Optional — link to HRMS Shift Type for matching |
| `department` | Optional — restrict rule to a department |
| `overtime_eligible` | Allow overtime calculation for this rule |

### Custom Fields

Created automatically by `after_install`:

| DocType | Field | Type | Description |
|---|---|---|---|
| Employee | `religion_category` | Select | Muslim / Non-Muslim |
| Attendance | `overtime_hours` | Float | Auto-filled overtime hours |
| Attendance | `overtime_entry` | Link | Link to Overtime Entry |

---

## How It Works

### Calculation Flow

1. **Trigger**: `Attendance.on_submit` fires `hooks_handler.on_attendance_submit()`
2. **Settings check**: Load Overtime Settings; skip if disabled or auto-create is off
3. **Rule matching**: `get_applicable_shift_rule()` finds the best-scoring rule for this attendance
4. **Checkin retrieval**: Get Employee Checkin records linked to this Attendance (with fallback search)
5. **Duration calc**: Compute actual working hours from first-IN to last-OUT checkin timestamps
6. **Scheduled hours**: Calculate from shift rule's check_in/check_out times (handles overnight)
7. **Net overtime**: `actual_hours - scheduled_hours - food_break + grace_adjustment`
8. **Rounding**: Apply configured rounding method
9. **Caps**: Enforce `minimum_overtime_minutes` and `max_overtime_hours_per_day`
10. **Rate**: Apply `default_overtime_rate_multiplier` or `holiday_overtime_rate_multiplier`
11. **Create entry**: Insert Overtime Entry with all calculated fields

### Overnight Shift Handling

**HRMS behavior** (critical to understand):

When a Shift Type has `start_time > end_time` (e.g. 23:30 → 07:30), HRMS treats it as an overnight shift:

- The `get_shift_timings()` function in HRMS detects `start_time > end_time` and enters the overnight branch
- A checkin at **23:30 on Jan 15** gets `shift_start = Jan 15 23:30` and `shift_end = Jan 16 07:30`
- A checkout at **07:30 on Jan 16** gets the **same** `shift_start = Jan 15 23:30` and `shift_end = Jan 16 07:30`
- HRMS groups checkins by `(employee, shift_start)` and creates ONE Attendance record
- The Attendance date is **Jan 15** (the `shift_start.date()`)

**Our app handles this by:**

- Using `is_overnight_shift` flag on shift rules to correctly calculate scheduled hours across midnight
- The `_get_checkin_logs()` function searches by `shift_start` date for fallback matching
- Duration is always calculated from full datetime timestamps (not time-only), so midnight crossing is automatic

**Known HRMS edge case**: If `last_sync_of_checkin` on the Shift Type is set to a value less than the shift duration, overnight OUT checkins may be skipped. Ensure `last_sync_of_checkin` ≥ shift duration.

### Ramadan Mode

When `ramadan_mode_enabled = 1` and today falls within `[ramadan_start_date, ramadan_end_date]`:

1. Shift rules with `applicable_period = "Ramadan"` get +100 priority in scoring
2. Muslim employees match rules with `employee_category = "Muslim"`
3. Non-Muslim employees match rules with `employee_category = "Non-Muslim"`
4. Rules with `employee_category = "All"` serve as fallback

Outside the Ramadan date range, only `Standard` period rules are considered.

### Shift Rule Matching (Scoring)

When multiple shift rules exist, the system picks the best match using a weighted score:

| Criterion | Points | Description |
|---|---|---|
| **Period match** | +100 | Ramadan rule during Ramadan period |
| **Category match** | +50 | Exact religion category match (Muslim/Non-Muslim) |
| **Shift type match** | +30 | Rule's `shift_type` matches Attendance's shift |
| **Department match** | +25 | Rule's `department` matches Employee's department |
| **Fallback** | +10 | Rules with `employee_category = "All"` |

The highest-scoring enabled rule wins. Ties are broken by the DB ordering.

---

## Shift Schedule Reference

### Standard Period (All Employees)

| Shift | Check-in | Check-out | Overnight | Scheduled | Food Break | Grace |
|---|---|---|---|---|---|---|
| Morning | 07:30 | 15:30 | No | 8h (7.5h net) | 30min | 15min |
| Evening | 15:30 | 23:30 | No | 8h (7.5h net) | 30min | 15min |
| Night | 23:30 | 07:30 | **Yes** | 8h (7.5h net) | 30min | 15min |

### Ramadan Period — Muslim Employees

| Shift | Check-in | Check-out | Overnight | Scheduled | Food Break | Grace |
|---|---|---|---|---|---|---|
| Factory Morning | 07:00 | 13:00 | No | 6h | None (fasting) | None |
| Admin Morning | 09:00 | 15:00 | No | 6h | None (fasting) | None |
| Factory Night | 00:00 | 19:30 | No | 19.5h (18.5h net) | 60min Suhoor | None |

### Ramadan Period — Non-Muslim Employees

| Shift | Check-in | Check-out | Overnight | Scheduled | Food Break | Grace |
|---|---|---|---|---|---|---|
| Factory Evening | 16:00 | 00:00 | **Yes** | 8h (7.5h net) | 30min | None |

---

## API Reference

All endpoints require authentication. Call via `desk.call()` or `frappe.call()`.

### `overtime.overtime.api.overtime.get_overtime_summary`

Get overtime summary for an employee in a given month.

```python
frappe.call(
    method="overtime.overtime.api.overtime.get_overtime_summary",
    args={
        "employee": "HR-EMP-0001",
        "month": "2025-03"     # YYYY-MM format
    }
)
```

**Response:**
```json
{
    "message": {
        "employee": "HR-EMP-0001",
        "month": "2025-03",
        "total_overtime_hours": 12.5,
        "total_payable_hours": 18.75,
        "total_entries": 8,
        "approved_entries": 6,
        "pending_entries": 2,
        "rejected_entries": 0,
        "entries": [...]
    }
}
```

### `overtime.overtime.api.overtime.recalculate_overtime`

Recalculate overtime for a date range (max 31 days). Deletes existing draft entries and recalculates.

```python
frappe.call(
    method="overtime.overtime.api.overtime.recalculate_overtime",
    args={
        "employee": "HR-EMP-0001",
        "from_date": "2025-03-01",
        "to_date": "2025-03-31"
    }
)
```

### `overtime.overtime.api.overtime.bulk_submit_overtime`

Bulk-submit multiple Overtime Entry records.

```python
frappe.call(
    method="overtime.overtime.api.overtime.bulk_submit_overtime",
    args={
        "entries": ["OT-HR-EMP-0001-0001", "OT-HR-EMP-0001-0002"]
    }
)
```

### `overtime.overtime.api.overtime.get_overtime_settings`

Get current Overtime Settings (for frontend display).

```python
frappe.call(
    method="overtime.overtime.api.overtime.get_overtime_settings"
)
```

---

## DocTypes

### Overtime Settings (Single)

Global configuration for overtime processing. One record per site.

### Overtime Shift Rule

Defines shift schedules with check-in/out times, breaks, grace periods, and category/period qualifiers. Named as `{shift_name}-{employee_category}-{applicable_period}`.

### Overtime Entry (Submittable)

Individual overtime records linked to Employee + Attendance. Named as `OT-{employee}-.####`.

**Fields**: employee, attendance, attendance_date, shift, overtime_hours, rate_multiplier, payable_overtime_hours, status (Draft/Approved/Rejected), and complete shift/checkin details.

---

## Extending / Customization

### Adding New Shift Rules

1. Go to **Overtime Shift Rule** → New
2. Fill in shift name, times, period, category
3. Set `overtime_eligible = 1`
4. Save — the rule will be matched automatically by the scoring engine

### Custom Rate Logic

Override `_get_rate_multiplier()` in `utils.py` if you need per-employee or per-department rates.

### Custom Hooks

The app hooks into `Attendance.on_submit` and `Attendance.on_cancel`. If you need to add custom logic, extend `hooks_handler.py` or add your own `doc_events` in a separate app.

### Adding Department-Specific Rules

Set the `department` field on a shift rule to restrict it. Department match adds +25 to the scoring, giving it priority over generic rules.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| No overtime calculated | Check **Overtime Settings** → `enabled` and `auto_create_overtime_entry` are checked |
| Wrong shift rule applied | Check scoring: verify `applicable_period`, `employee_category`, `shift_type`, `department` on rules |
| Overnight shift gives 0 hours | Ensure `is_overnight_shift` is checked on the rule; verify HRMS Shift Type has `start_time > end_time` |
| Checkins not found | Ensure Employee Checkins have `attendance` linked, or `shift_start` set for fallback search |
| Ramadan rules not matching | Verify `ramadan_mode_enabled = 1`, dates are set, and today falls within them |
| Grace period not applying | Check `allow_late_early_exception` is checked and `late_early_grace_minutes` > 0 on the shift rule |
| Rate multiplier wrong | Check `default_overtime_rate_multiplier` / `holiday_overtime_rate_multiplier` in settings |
| Rounding not working | Check `overtime_rounding` is not "No Rounding" and `rounding_interval_minutes` > 0 |

### Logs

```bash
# Check overtime-specific logs
bench --site your-site.local console
>>> frappe.get_doc("Error Log", {"method": ["like", "%overtime%"]})

# Check scheduler logs
tail -f logs/scheduler.log | grep overtime
```

---

## File Structure

```
overtime/
├── README.md                           # This file
├── pyproject.toml                      # Package metadata
├── overtime/
│   ├── __init__.py
│   ├── hooks.py                        # App hooks (doc_events, scheduler, fixtures)
│   └── overtime/
│       ├── __init__.py
│       ├── setup.py                    # after_install: custom fields + default data
│       ├── utils.py                    # Core overtime calculation engine
│       ├── hooks_handler.py            # Attendance event handlers + scheduler
│       ├── api/
│       │   ├── __init__.py
│       │   └── overtime.py             # Whitelisted API endpoints
│       └── doctype/
│           ├── overtime_settings/
│           │   ├── overtime_settings.json
│           │   └── overtime_settings.py
│           ├── overtime_shift_rule/
│           │   ├── overtime_shift_rule.json
│           │   └── overtime_shift_rule.py
│           └── overtime_entry/
│               ├── overtime_entry.json
│               └── overtime_entry.py
```

---

## Contributing

```bash
cd apps/overtime
pre-commit install
```

Uses: ruff, eslint, prettier, pyupgrade

---

## License

MIT
