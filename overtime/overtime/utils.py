# Copyright (c) 2026, Ali Raza and contributors
# For license information, please see license.txt

"""
Core overtime calculation engine.

This module handles:
1. Calculating overtime hours from Employee Checkin logs
2. Applying shift rules (standard + Ramadan)
3. Handling food break deductions
4. Rounding and capping overtime
5. Auto-creating Overtime Entry records
6. Proper overnight/night shift support (shifts crossing midnight)

Overnight Shift Handling:
  HRMS correctly resolves overnight shifts by setting identical shift_start/shift_end
  on both the IN (e.g. 7PM) and OUT (e.g. 7AM next day) checkins. Both checkins
  share the same shift_start datetime, so grouping works. Attendance is marked on
  shift_start.date() (the start date of the shift).

  This module respects those timestamps and computes overtime from the actual checkin
  duration vs the scheduled shift hours.
"""

import math
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import (
    add_days,
    cint,
    flt,
    get_datetime,
    get_time,
    getdate,
    today,
)


def calculate_overtime_for_attendance(attendance_name):
    """
    Calculate overtime for a specific attendance record.
    Called after attendance is marked by HRMS shift processing.

    For overnight shifts (e.g. 23:30-07:30), HRMS groups checkins by
    (employee, shift_start) and marks attendance on shift_start.date().
    This function reads those already-resolved values.

    Args:
        attendance_name: Name of the Attendance document

    Returns:
        Overtime Entry name if created, else None
    """
    try:
        settings = frappe.get_cached_doc("Overtime Settings")
    except Exception:
        frappe.log_error("Overtime Settings not found", "Overtime Calculation Error")
        return None

    if not settings.enabled:
        return None

    attendance = frappe.get_doc("Attendance", attendance_name)

    # Only process Present/Half Day attendance
    if attendance.status not in ("Present", "Half Day"):
        return None

    # Skip if overtime entry already exists for this employee+date
    if frappe.db.exists(
        "Overtime Entry",
        {
            "employee": attendance.employee,
            "attendance_date": attendance.attendance_date,
            "docstatus": ["!=", 2],
        },
    ):
        return None

    # Get checkin logs for this attendance (HRMS links checkins to attendance)
    checkin_logs = _get_checkin_logs(attendance_name, attendance)

    if not checkin_logs:
        return None

    employee = attendance.employee
    shift_type = attendance.shift or (checkin_logs[0].shift if checkin_logs else None)

    # Get applicable shift rule
    from overtime.overtime.doctype.overtime_shift_rule.overtime_shift_rule import (
        get_applicable_shift_rule,
    )

    shift_rule = get_applicable_shift_rule(
        employee, shift_type=shift_type, date=attendance.attendance_date
    )

    # Check if shift rule says overtime is not eligible
    if shift_rule and not cint(shift_rule.overtime_eligible):
        return None

    # Calculate overtime
    overtime_data = _compute_overtime(
        checkin_logs=checkin_logs,
        attendance=attendance,
        shift_rule=shift_rule,
        settings=settings,
    )

    if not overtime_data or overtime_data["overtime_minutes"] <= 0:
        return None

    # Auto-create overtime entry if enabled
    if settings.auto_create_overtime_entry:
        return _create_overtime_entry(overtime_data, attendance, shift_rule, settings)

    return None


def _get_checkin_logs(attendance_name, attendance):
    """
    Get Employee Checkin logs linked to an attendance record.
    Falls back to searching by employee + shift_start if no direct link exists.

    For overnight shifts, HRMS sets identical shift_start/shift_end on both
    the evening IN checkin and next-morning OUT checkin. This ensures they
    are grouped together under the same attendance.
    """
    # Primary: checkins directly linked to this attendance
    checkin_logs = frappe.get_all(
        "Employee Checkin",
        filters={"attendance": attendance_name},
        fields=[
            "name", "time", "log_type", "shift",
            "shift_start", "shift_end",
            "shift_actual_start", "shift_actual_end",
            "employee",
        ],
        order_by="time asc",
    )

    if checkin_logs:
        return checkin_logs

    # Fallback: find checkins by employee + date range matching shift window
    # This handles edge cases where attendance link is missing
    att_date = getdate(attendance.attendance_date)
    start_of_day = get_datetime(f"{att_date} 00:00:00")
    # For overnight shifts, the OUT checkin may be up to 24h after start_of_day
    end_of_next_day = get_datetime(f"{add_days(att_date, 1)} 23:59:59")

    checkin_logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": attendance.employee,
            "time": ["between", [start_of_day, end_of_next_day]],
            "shift": attendance.shift,
        },
        fields=[
            "name", "time", "log_type", "shift",
            "shift_start", "shift_end",
            "shift_actual_start", "shift_actual_end",
            "employee",
        ],
        order_by="time asc",
    )

    # Filter only checkins whose shift_start date matches the attendance date
    # This is crucial for overnight shifts where shift_start.date() == attendance_date
    if checkin_logs:
        filtered = []
        for log in checkin_logs:
            if log.shift_start:
                shift_start_date = getdate(get_datetime(log.shift_start))
                if shift_start_date == att_date:
                    filtered.append(log)
            else:
                # No shift_start assigned - include if time is on attendance date
                if getdate(get_datetime(log.time)) == att_date:
                    filtered.append(log)
        return filtered or checkin_logs

    return checkin_logs


def _compute_overtime(checkin_logs, attendance, shift_rule, settings):
    """
    Core overtime computation logic.

    For overnight shifts:
      - actual_working_hours comes from attendance.working_hours (calculated by HRMS
        from time diff between first IN and last OUT, which may span two calendar days)
      - scheduled_hours comes from shift_rule.total_shift_hours or shift_start/shift_end
        (HRMS correctly sets shift_end > shift_start even across midnight)
      - overtime = actual_working_hours - scheduled_hours - food_break

    Args:
        checkin_logs: List of Employee Checkin records
        attendance: Attendance document
        shift_rule: OvertimeShiftRule document (or None)
        settings: OvertimeSettings document

    Returns:
        dict with overtime calculation details, or None
    """
    if not checkin_logs:
        return None

    # Determine actual working hours from attendance (HRMS already computed this)
    actual_working_hours = flt(attendance.working_hours) if attendance.working_hours else 0

    if not actual_working_hours and len(checkin_logs) >= 2:
        # Fallback: calculate from first check-in to last check-out
        # This works correctly for overnight shifts because datetime math
        # handles crossing midnight (e.g. Feb 10 23:30 to Feb 11 07:30 = 8 hours)
        first_in = get_datetime(checkin_logs[0].time)
        last_out = get_datetime(checkin_logs[-1].time)
        diff_seconds = (last_out - first_in).total_seconds()
        if diff_seconds > 0:
            actual_working_hours = round(diff_seconds / 3600, 2)

    if actual_working_hours <= 0:
        return None

    # Determine scheduled shift hours
    scheduled_hours = _get_scheduled_hours(checkin_logs, shift_rule, attendance)

    if scheduled_hours <= 0:
        return None

    # Determine check-in/check-out times
    first_checkin = get_datetime(checkin_logs[0].time)
    last_checkout = get_datetime(checkin_logs[-1].time)

    # Calculate food break deduction
    food_break_minutes = 0
    food_break_deducted = False
    if shift_rule and cint(shift_rule.has_food_break) and cint(shift_rule.food_break_included_in_shift):
        food_break_minutes = cint(shift_rule.food_break_duration_minutes) or 0
        food_break_deducted = True
        # Food break is excluded from shift hours (already deducted from scheduled_hours
        # via calculate_total_shift_hours). We also deduct from actual working hours.
        actual_working_hours -= food_break_minutes / 60

    # Apply late/early exception grace period
    # If the employee checked in slightly late or left slightly early,
    # don't penalize them - use the scheduled hours as minimum baseline
    grace_minutes = 0
    if shift_rule and cint(shift_rule.allow_late_early_exception):
        grace_minutes = cint(shift_rule.late_early_grace_minutes) or 0

    # Calculate raw overtime: minutes worked beyond shift duration
    raw_overtime_minutes = (actual_working_hours - scheduled_hours) * 60

    # If negative but within grace period, treat as zero overtime (not negative)
    if raw_overtime_minutes < 0 and abs(raw_overtime_minutes) <= grace_minutes:
        return None

    if raw_overtime_minutes <= 0:
        return None

    # Apply minimum overtime threshold
    min_ot_minutes = _get_min_overtime_minutes(shift_rule, settings)
    if raw_overtime_minutes < min_ot_minutes:
        return None

    # Apply rounding
    rounded_overtime_minutes = _apply_rounding(raw_overtime_minutes, settings)

    if rounded_overtime_minutes <= 0:
        return None

    # Apply max cap
    max_ot_hours = _get_max_overtime_hours(shift_rule, settings)
    if max_ot_hours > 0:
        max_ot_minutes = max_ot_hours * 60
        rounded_overtime_minutes = min(rounded_overtime_minutes, max_ot_minutes)

    # Check if holiday
    is_holiday = _check_holiday(attendance)

    # Determine rate multiplier (holiday gets higher rate)
    rate_multiplier = _get_rate_multiplier(shift_rule, settings, is_holiday)

    return {
        "overtime_minutes": rounded_overtime_minutes,
        "overtime_hours": round(rounded_overtime_minutes / 60, 2),
        "actual_working_hours": round(actual_working_hours, 2),
        "scheduled_hours": scheduled_hours,
        "first_checkin": first_checkin,
        "last_checkout": last_checkout,
        "food_break_minutes": food_break_minutes,
        "food_break_deducted": food_break_deducted,
        "rate_multiplier": rate_multiplier,
        "is_holiday": is_holiday,
        "raw_overtime_minutes": round(raw_overtime_minutes, 2),
        "grace_minutes_applied": grace_minutes,
    }


def _get_scheduled_hours(checkin_logs, shift_rule, attendance):
    """
    Determine scheduled shift hours.

    Priority order:
      1. Overtime Shift Rule total_shift_hours (most accurate, configured by admin)
      2. Employee Checkin shift_start/shift_end (set by HRMS, handles overnight correctly)
      3. Shift Type start_time/end_time (handles overnight via time comparison)
      4. Default 8.0 hours

    For overnight shifts:
      HRMS sets shift_start and shift_end as full datetimes (not just times),
      so shift_end is always > shift_start even when crossing midnight:
        shift_start = Feb 10, 23:30  ->  shift_end = Feb 11, 07:30  ->  8 hours
    """
    # Priority 1: Overtime Shift Rule (admin-configured, most reliable)
    if shift_rule and flt(shift_rule.total_shift_hours) > 0:
        return flt(shift_rule.total_shift_hours)

    # Priority 2: Calculate from checkin's shift_start/shift_end (datetime, not time)
    if checkin_logs and checkin_logs[0].shift_start and checkin_logs[0].shift_end:
        shift_start = get_datetime(checkin_logs[0].shift_start)
        shift_end = get_datetime(checkin_logs[0].shift_end)
        diff_seconds = (shift_end - shift_start).total_seconds()
        if diff_seconds > 0:
            return round(diff_seconds / 3600, 2)

    # Priority 3: Shift Type start_time/end_time
    shift_type_name = attendance.shift if attendance else None
    if shift_type_name:
        try:
            shift_type = frappe.get_cached_doc("Shift Type", shift_type_name)
            start = get_time(shift_type.start_time)
            end = get_time(shift_type.end_time)

            base = datetime(2026, 1, 1)
            dt_start = datetime.combine(base, start)
            dt_end = datetime.combine(base, end)
            # Overnight shift: end time is on next day
            if dt_end <= dt_start:
                dt_end += timedelta(days=1)

            hours = round((dt_end - dt_start).total_seconds() / 3600, 2)
            if hours > 0:
                return hours
        except frappe.DoesNotExistError:
            pass

    # Priority 4: Default 8 hours
    return 8.0


def _get_min_overtime_minutes(shift_rule, settings):
    """Get minimum overtime threshold in minutes."""
    if shift_rule and cint(shift_rule.min_overtime_minutes) > 0:
        return cint(shift_rule.min_overtime_minutes)
    return cint(settings.minimum_overtime_minutes) or 0


def _get_max_overtime_hours(shift_rule, settings):
    """Get maximum overtime hours cap."""
    if shift_rule and flt(shift_rule.max_overtime_hours) > 0:
        return flt(shift_rule.max_overtime_hours)
    return flt(settings.max_overtime_hours_per_day) or 0


def _get_rate_multiplier(shift_rule, settings, is_holiday=False):
    """Determine the overtime rate multiplier."""
    if is_holiday:
        return flt(settings.holiday_overtime_rate_multiplier) or 2.0

    if shift_rule and flt(shift_rule.overtime_rate_multiplier) > 0:
        return flt(shift_rule.overtime_rate_multiplier)

    return flt(settings.default_overtime_rate_multiplier) or 1.5


def _check_holiday(attendance):
    """Check if the attendance date is a holiday."""
    if not attendance:
        return False

    employee = attendance.employee
    att_date = getdate(attendance.attendance_date)

    try:
        # Check via Holiday List on Employee -> Company fallback
        holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
        if not holiday_list:
            company = frappe.db.get_value("Employee", employee, "company")
            if company:
                holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

        if holiday_list:
            return bool(
                frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": att_date})
            )
    except Exception:
        pass

    return False


def _apply_rounding(overtime_minutes, settings):
    """
    Apply rounding to overtime minutes.

    Rounding modes:
      - No Rounding: keep raw value
      - Round Up:    ceil to interval (e.g. 23 -> 30 for 15-min interval)
      - Round Down:  floor to interval (e.g. 23 -> 15)
      - Round to Nearest: round to closest interval (e.g. 23 -> 30, 7 -> 0)
    """
    rounding = settings.overtime_rounding or "No Rounding"
    interval = cint(settings.rounding_interval_minutes) or 15

    if rounding == "No Rounding" or interval <= 0:
        return overtime_minutes

    if rounding == "Round Up":
        return math.ceil(overtime_minutes / interval) * interval
    elif rounding == "Round Down":
        return math.floor(overtime_minutes / interval) * interval
    elif rounding == "Round to Nearest":
        return round(overtime_minutes / interval) * interval

    return overtime_minutes


def _create_overtime_entry(overtime_data, attendance, shift_rule, settings):
    """Create an Overtime Entry document from computed overtime data."""
    try:
        entry = frappe.new_doc("Overtime Entry")
        entry.employee = attendance.employee
        entry.attendance_date = attendance.attendance_date
        entry.attendance = attendance.name
        entry.shift_type = attendance.shift
        entry.overtime_shift_rule = shift_rule.name if shift_rule else None

        # Shift times (from shift_start/shift_end on checkins)
        entry.shift_start_time = overtime_data.get("first_checkin")
        entry.shift_end_time = overtime_data.get("last_checkout")
        entry.scheduled_shift_hours = overtime_data["scheduled_hours"]

        # Actual checkin/checkout times
        entry.actual_check_in = overtime_data["first_checkin"]
        entry.actual_check_out = overtime_data["last_checkout"]
        entry.actual_working_hours = overtime_data["actual_working_hours"]

        # Overtime calculation results
        entry.overtime_hours = overtime_data["overtime_hours"]
        entry.overtime_minutes = overtime_data["overtime_minutes"]
        entry.overtime_rate_multiplier = overtime_data["rate_multiplier"]
        entry.is_holiday_overtime = overtime_data["is_holiday"]

        # Food break
        entry.food_break_deducted = overtime_data["food_break_deducted"]
        entry.food_break_minutes = overtime_data["food_break_minutes"]

        # Status
        if settings.require_approval:
            entry.status = "Pending Approval"
        else:
            entry.status = "Approved"

        entry.remarks = _build_remarks(overtime_data, shift_rule)

        entry.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.logger("overtime").info(
            f"Overtime Entry {entry.name} created for {attendance.employee} "
            f"on {attendance.attendance_date}: {overtime_data['overtime_hours']}h"
        )

        return entry.name

    except frappe.DuplicateEntryError:
        frappe.logger("overtime").warning(
            f"Duplicate Overtime Entry for {attendance.employee} on {attendance.attendance_date}"
        )
        return None
    except Exception as e:
        frappe.log_error(
            f"Failed to create Overtime Entry for {attendance.employee}: {str(e)}",
            "Overtime Entry Creation Error",
        )
        return None


def _build_remarks(overtime_data, shift_rule):
    """Build human-readable remarks for the overtime entry."""
    parts = []
    parts.append(
        f"Scheduled: {overtime_data['scheduled_hours']}h | "
        f"Actual: {overtime_data['actual_working_hours']}h | "
        f"Overtime: {overtime_data['overtime_hours']}h ({overtime_data['overtime_minutes']} min)"
    )

    if overtime_data.get("food_break_deducted"):
        parts.append(f"Food break: {overtime_data['food_break_minutes']}min deducted")

    if overtime_data.get("is_holiday"):
        parts.append("Holiday overtime (rate: {0}x)".format(overtime_data.get("rate_multiplier", 2.0)))

    if shift_rule:
        parts.append(f"Rule: {shift_rule.shift_name}")

    return " | ".join(parts)


def process_overtime_for_date(date=None, employee=None):
    """
    Process overtime for all attendance records on a given date.
    Can be called from scheduler or manually.

    For overnight shifts, the attendance_date is the shift start date
    (set by HRMS). So filtering by date correctly picks up night shifts
    that started on that date, even if the employee checked out the next day.

    Args:
        date: Date to process (default: yesterday)
        employee: Optional employee filter

    Returns:
        Number of Overtime Entries created
    """
    try:
        settings = frappe.get_cached_doc("Overtime Settings")
    except Exception:
        return 0

    if not settings.enabled:
        return 0

    if not date:
        date = add_days(getdate(today()), -1)
    else:
        date = getdate(date)

    filters = {
        "attendance_date": date,
        "status": ["in", ["Present", "Half Day"]],
        "docstatus": 1,
    }
    if employee:
        filters["employee"] = employee

    attendance_list = frappe.get_all("Attendance", filters=filters, pluck="name")

    created = 0
    for att_name in attendance_list:
        try:
            result = calculate_overtime_for_attendance(att_name)
            if result:
                created += 1
        except Exception as e:
            frappe.log_error(
                f"Overtime processing failed for Attendance {att_name}: {str(e)}",
                "Overtime Batch Processing Error",
            )

    if created:
        frappe.logger("overtime").info(
            f"Processed overtime for {date}: {created}/{len(attendance_list)} entries created"
        )

    return created


@frappe.whitelist()
def process_overtime_manually(date=None, employee=None):
    """Whitelisted method to process overtime manually from the UI."""
    frappe.only_for(["HR Manager", "System Manager"])

    date = date or None
    employee = employee or None

    count = process_overtime_for_date(date=date, employee=employee)
    target = date or "yesterday"
    if count:
        frappe.msgprint(_(f"{count} Overtime Entry(ies) created for {target}."))
    else:
        frappe.msgprint(_("No overtime found for the specified criteria."))
    return count
