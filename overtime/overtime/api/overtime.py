# Copyright (c) 2026, Ali Raza and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today


@frappe.whitelist()
def get_overtime_summary(employee=None, from_date=None, to_date=None):
    """
    Get overtime summary for an employee or all employees.

    Args:
        employee: Employee ID (optional, defaults to all)
        from_date: Start date (optional, defaults to current month start)
        to_date: End date (optional, defaults to today)

    Returns:
        dict with summary data including totals and per-employee breakdown
    """
    if not from_date:
        from frappe.utils import get_first_day
        from_date = get_first_day(today())
    if not to_date:
        to_date = today()

    filters = {
        "attendance_date": ["between", [getdate(from_date), getdate(to_date)]],
        "docstatus": ["!=", 2],
    }
    if employee:
        filters["employee"] = employee

    entries = frappe.get_all(
        "Overtime Entry",
        filters=filters,
        fields=[
            "name", "employee", "employee_name", "department",
            "attendance_date", "overtime_hours", "overtime_minutes",
            "overtime_rate_multiplier", "is_holiday_overtime",
            "status", "shift_type", "overtime_shift_rule",
            "actual_working_hours", "scheduled_shift_hours",
        ],
        order_by="attendance_date desc",
    )

    # Calculate totals
    total_hours = sum(flt(e.overtime_hours) for e in entries)
    total_entries = len(entries)
    approved_entries = len([e for e in entries if e.status == "Approved"])
    pending_entries = len([e for e in entries if e.status == "Pending Approval"])
    rejected_entries = len([e for e in entries if e.status == "Rejected"])
    holiday_entries = len([e for e in entries if e.is_holiday_overtime])

    # Group by employee
    by_employee = {}
    for e in entries:
        if e.employee not in by_employee:
            by_employee[e.employee] = {
                "employee": e.employee,
                "employee_name": e.employee_name,
                "department": e.department,
                "total_hours": 0,
                "total_entries": 0,
                "entries": [],
            }
        by_employee[e.employee]["total_hours"] += flt(e.overtime_hours)
        by_employee[e.employee]["total_entries"] += 1
        by_employee[e.employee]["entries"].append(e)

    # Round totals
    for emp_data in by_employee.values():
        emp_data["total_hours"] = round(emp_data["total_hours"], 2)

    return {
        "total_hours": round(total_hours, 2),
        "total_entries": total_entries,
        "approved_entries": approved_entries,
        "pending_entries": pending_entries,
        "rejected_entries": rejected_entries,
        "holiday_entries": holiday_entries,
        "from_date": str(from_date),
        "to_date": str(to_date),
        "by_employee": list(by_employee.values()),
        "entries": entries,
    }


@frappe.whitelist()
def get_employee_overtime_details(employee, month=None, year=None):
    """
    Get detailed overtime data for a specific employee in a month.

    Args:
        employee: Employee ID
        month: Month number (1-12, defaults to current)
        year: Year (defaults to current)

    Returns:
        dict with monthly overtime details
    """
    from frappe.utils import get_first_day, get_last_day
    from datetime import date

    today_date = date.today()
    month = cint(month) or today_date.month
    year = cint(year) or today_date.year

    first_day = get_first_day(f"{year}-{month:02d}-01")
    last_day = get_last_day(f"{year}-{month:02d}-01")

    entries = frappe.get_all(
        "Overtime Entry",
        filters={
            "employee": employee,
            "attendance_date": ["between", [first_day, last_day]],
            "docstatus": ["!=", 2],
        },
        fields=["*"],
        order_by="attendance_date asc",
    )

    total_hours = sum(flt(e.overtime_hours) for e in entries)
    total_days = len(entries)
    approved_hours = sum(flt(e.overtime_hours) for e in entries if e.status == "Approved")
    holiday_hours = sum(flt(e.overtime_hours) for e in entries if e.is_holiday_overtime)

    return {
        "employee": employee,
        "employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
        "month": month,
        "year": year,
        "total_overtime_hours": round(total_hours, 2),
        "approved_overtime_hours": round(approved_hours, 2),
        "holiday_overtime_hours": round(holiday_hours, 2),
        "total_overtime_days": total_days,
        "entries": entries,
    }


@frappe.whitelist()
def bulk_approve_overtime(entries):
    """
    Bulk approve overtime entries.

    Args:
        entries: List of Overtime Entry names or JSON string
    """
    frappe.only_for(["HR Manager", "System Manager"])

    if isinstance(entries, str):
        entries = json.loads(entries)

    approved = 0
    errors = []
    for entry_name in entries:
        try:
            doc = frappe.get_doc("Overtime Entry", entry_name)
            if doc.docstatus == 0 and doc.status in ("Draft", "Pending Approval"):
                doc.status = "Approved"
                doc.approved_by = frappe.session.user
                doc.approval_date = getdate(today())
                doc.save(ignore_permissions=True)
                approved += 1
        except Exception as e:
            errors.append(f"{entry_name}: {str(e)}")
            frappe.log_error(f"Failed to approve {entry_name}: {str(e)}")

    frappe.db.commit()

    msg = _(f"{approved} entries approved.")
    if errors:
        msg += _(" {0} errors occurred.").format(len(errors))

    frappe.msgprint(msg)
    return {"approved": approved, "errors": errors}


@frappe.whitelist()
def bulk_submit_overtime(entries):
    """
    Bulk submit approved overtime entries.

    Args:
        entries: List of Overtime Entry names or JSON string
    """
    frappe.only_for(["HR Manager", "System Manager"])

    if isinstance(entries, str):
        entries = json.loads(entries)

    submitted = 0
    errors = []
    for entry_name in entries:
        try:
            doc = frappe.get_doc("Overtime Entry", entry_name)
            if doc.docstatus == 0 and doc.status == "Approved":
                doc.submit()
                submitted += 1
        except Exception as e:
            errors.append(f"{entry_name}: {str(e)}")
            frappe.log_error(f"Failed to submit {entry_name}: {str(e)}")

    frappe.db.commit()

    msg = _(f"{submitted} entries submitted.")
    if errors:
        msg += _(" {0} errors occurred.").format(len(errors))

    frappe.msgprint(msg)
    return {"submitted": submitted, "errors": errors}


@frappe.whitelist()
def get_shift_rules_for_employee(employee, date=None):
    """
    Get the applicable shift rule for an employee on a given date.
    Useful for the UI to show which shift rule will be applied.

    Args:
        employee: Employee ID
        date: Date to check (defaults to today)
    """
    from overtime.overtime.doctype.overtime_shift_rule.overtime_shift_rule import (
        get_applicable_shift_rule,
        get_employee_category,
    )

    if not date:
        date = today()

    rule = get_applicable_shift_rule(employee, date=date)
    category = get_employee_category(employee)

    return {
        "employee_category": category,
        "date": str(date),
        "applicable_rule": rule,
    }


@frappe.whitelist()
def recalculate_overtime(employee=None, from_date=None, to_date=None):
    """
    Recalculate overtime for a date range. Deletes existing DRAFT entries
    and recreates them. Submitted entries are left untouched.

    Args:
        employee: Optional employee filter
        from_date: Start date (required)
        to_date: End date (required)
    """
    frappe.only_for(["HR Manager", "System Manager"])

    from overtime.overtime.utils import process_overtime_for_date

    if not from_date or not to_date:
        frappe.throw(_("Please provide both from_date and to_date"))

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw(_("From date cannot be after to date"))

    if (to_date - from_date).days > 31:
        frappe.throw(_("Date range cannot exceed 31 days for recalculation"))

    # Delete existing DRAFT overtime entries in the range
    filters = {
        "attendance_date": ["between", [from_date, to_date]],
        "docstatus": 0,  # Only drafts
    }
    if employee:
        filters["employee"] = employee

    existing = frappe.get_all("Overtime Entry", filters=filters, pluck="name")
    for entry_name in existing:
        frappe.delete_doc("Overtime Entry", entry_name, ignore_permissions=True)

    frappe.db.commit()

    # Recalculate
    total_created = 0
    current_date = from_date
    while current_date <= to_date:
        count = process_overtime_for_date(date=current_date, employee=employee)
        total_created += count or 0
        current_date = add_days(current_date, 1)

    frappe.msgprint(
        _(f"Recalculated: {total_created} entries created, {len(existing)} old drafts removed.")
    )
    return {"created": total_created, "removed": len(existing)}


@frappe.whitelist()
def get_overtime_settings():
    """Get current overtime settings (for frontend display)."""
    settings = frappe.get_cached_doc("Overtime Settings")
    return {
        "enabled": cint(settings.enabled),
        "overtime_based_on": settings.overtime_based_on,
        "minimum_overtime_minutes": cint(settings.minimum_overtime_minutes),
        "max_overtime_hours_per_day": flt(settings.max_overtime_hours_per_day),
        "overtime_rounding": settings.overtime_rounding,
        "rounding_interval_minutes": cint(settings.rounding_interval_minutes),
        "default_overtime_rate_multiplier": flt(settings.default_overtime_rate_multiplier),
        "holiday_overtime_rate_multiplier": flt(settings.holiday_overtime_rate_multiplier),
        "require_approval": cint(settings.require_approval),
        "auto_create_overtime_entry": cint(settings.auto_create_overtime_entry),
        "ramadan_mode_enabled": cint(settings.ramadan_mode_enabled),
        "ramadan_start_date": str(settings.ramadan_start_date) if settings.ramadan_start_date else None,
        "ramadan_end_date": str(settings.ramadan_end_date) if settings.ramadan_end_date else None,
    }


@frappe.whitelist()
def get_all_shift_rules(period=None, category=None, enabled_only=True):
    """
    Get all Overtime Shift Rules, optionally filtered.

    Args:
        period: 'Standard' or 'Ramadan' (optional)
        category: 'All', 'Muslim', or 'Non-Muslim' (optional)
        enabled_only: Only return enabled rules (default True)

    Returns:
        list of shift rule dicts
    """
    filters = {}
    if cint(enabled_only):
        filters["enabled"] = 1
    if period:
        filters["applicable_period"] = period
    if category:
        filters["employee_category"] = category

    return frappe.get_all(
        "Overtime Shift Rule",
        filters=filters,
        fields=[
            "name", "shift_name", "shift_type", "applicable_period",
            "employee_category", "department", "enabled",
            "check_in_time", "check_out_time", "total_shift_hours",
            "is_overnight_shift", "allow_late_early_exception",
            "late_early_grace_minutes", "has_food_break",
            "food_break_duration_minutes", "food_break_type",
            "food_break_included_in_shift", "overtime_eligible",
            "min_overtime_minutes", "max_overtime_hours",
            "overtime_rate_multiplier", "notes",
        ],
        order_by="applicable_period, employee_category, shift_name",
    )


@frappe.whitelist()
def get_employee_shift_info(employee, date=None):
    """
    Get comprehensive shift information for an employee on a given date.
    Useful for client scripts on Attendance, Employee, and Overtime Entry forms.

    Returns the employee's:
      - Religion category (Muslim/Non-Muslim/All)
      - Current Shift Assignment (from HRMS)
      - Default shift (from Employee master)
      - Applicable Overtime Shift Rule (with full details)
      - Whether the date is in Ramadan period
      - Scheduled working hours for the shift

    Args:
        employee: Employee ID
        date: Date to check (defaults to today)

    Returns:
        dict with shift details
    """
    if not date:
        date = today()
    date = getdate(date)

    from overtime.overtime.doctype.overtime_shift_rule.overtime_shift_rule import (
        get_applicable_shift_rule,
        get_employee_category,
    )

    emp_data = frappe.db.get_value(
        "Employee", employee,
        ["employee_name", "default_shift", "department", "company",
         "custom_employee_religion_category"],
        as_dict=True,
    )
    if not emp_data:
        frappe.throw(_("Employee {0} not found").format(employee))

    # Get current shift assignment from HRMS
    shift_assignment = frappe.db.get_value(
        "Shift Assignment",
        {
            "employee": employee,
            "start_date": ["<=", date],
            "docstatus": 1,
            "status": "Active",
        },
        ["name", "shift_type", "start_date", "end_date"],
        as_dict=True,
        order_by="start_date desc",
    )

    # Determine active shift type
    active_shift = None
    if shift_assignment:
        # Check end_date if it exists
        if shift_assignment.end_date and getdate(shift_assignment.end_date) < date:
            active_shift = emp_data.default_shift  # Assignment expired
        else:
            active_shift = shift_assignment.shift_type
    else:
        active_shift = emp_data.default_shift

    # Get applicable overtime shift rule
    category = get_employee_category(employee)
    rule = get_applicable_shift_rule(employee, shift_type=active_shift, date=date)

    # Check Ramadan status
    is_ramadan = False
    try:
        settings = frappe.get_cached_doc("Overtime Settings")
        if (
            cint(settings.ramadan_mode_enabled)
            and settings.ramadan_start_date
            and settings.ramadan_end_date
        ):
            if getdate(settings.ramadan_start_date) <= date <= getdate(settings.ramadan_end_date):
                is_ramadan = True
    except Exception:
        pass

    result = {
        "employee": employee,
        "employee_name": emp_data.employee_name,
        "department": emp_data.department,
        "company": emp_data.company,
        "employee_category": category,
        "default_shift": emp_data.default_shift,
        "active_shift": active_shift,
        "shift_assignment": shift_assignment,
        "is_ramadan": is_ramadan,
        "date": str(date),
        "applicable_rule": None,
        "scheduled_hours": 0,
        "overtime_eligible": False,
    }

    if rule:
        result["applicable_rule"] = {
            "name": rule.name,
            "shift_name": rule.shift_name,
            "shift_type": rule.shift_type,
            "applicable_period": rule.applicable_period,
            "employee_category": rule.employee_category,
            "check_in_time": str(rule.check_in_time),
            "check_out_time": str(rule.check_out_time),
            "total_shift_hours": flt(rule.total_shift_hours),
            "is_overnight_shift": cint(rule.is_overnight_shift),
            "has_food_break": cint(rule.has_food_break),
            "food_break_duration_minutes": cint(rule.food_break_duration_minutes),
            "food_break_type": rule.food_break_type,
            "allow_late_early_exception": cint(rule.allow_late_early_exception),
            "late_early_grace_minutes": cint(rule.late_early_grace_minutes),
            "overtime_rate_multiplier": flt(rule.overtime_rate_multiplier),
        }
        result["scheduled_hours"] = flt(rule.total_shift_hours)
        result["overtime_eligible"] = cint(rule.overtime_eligible)

    return result


@frappe.whitelist()
def check_ramadan_status(date=None):
    """
    Check whether a given date falls within the configured Ramadan period.

    Args:
        date: Date to check (defaults to today)

    Returns:
        dict with ramadan_mode_enabled, is_ramadan, start_date, end_date
    """
    if not date:
        date = today()
    date = getdate(date)

    result = {
        "date": str(date),
        "ramadan_mode_enabled": False,
        "is_ramadan": False,
        "ramadan_start_date": None,
        "ramadan_end_date": None,
    }

    try:
        settings = frappe.get_cached_doc("Overtime Settings")
        result["ramadan_mode_enabled"] = bool(cint(settings.ramadan_mode_enabled))
        if settings.ramadan_start_date:
            result["ramadan_start_date"] = str(settings.ramadan_start_date)
        if settings.ramadan_end_date:
            result["ramadan_end_date"] = str(settings.ramadan_end_date)

        if (
            cint(settings.ramadan_mode_enabled)
            and settings.ramadan_start_date
            and settings.ramadan_end_date
        ):
            if getdate(settings.ramadan_start_date) <= date <= getdate(settings.ramadan_end_date):
                result["is_ramadan"] = True
    except Exception:
        pass

    return result


@frappe.whitelist()
def bulk_reject_overtime(entries, reason=None):
    """
    Bulk reject overtime entries.

    Args:
        entries: List of Overtime Entry names or JSON string
        reason: Optional rejection reason
    """
    frappe.only_for(["HR Manager", "System Manager"])

    if isinstance(entries, str):
        entries = json.loads(entries)

    rejected = 0
    errors = []
    for entry_name in entries:
        try:
            doc = frappe.get_doc("Overtime Entry", entry_name)
            if doc.docstatus == 0 and doc.status in ("Draft", "Pending Approval"):
                doc.status = "Rejected"
                if reason:
                    doc.remarks = ((doc.remarks or "") + f"\nRejection Reason: {reason}").strip()
                doc.save(ignore_permissions=True)
                rejected += 1
        except Exception as e:
            errors.append(f"{entry_name}: {str(e)}")
            frappe.log_error(f"Failed to reject {entry_name}: {str(e)}")

    frappe.db.commit()

    msg = _(f"{rejected} entries rejected.")
    if errors:
        msg += _(" {0} errors occurred.").format(len(errors))

    frappe.msgprint(msg)
    return {"rejected": rejected, "errors": errors}


@frappe.whitelist()
def toggle_ramadan_mode(enabled, start_date=None, end_date=None):
    """
    Quick toggle for Ramadan mode from the UI.

    Args:
        enabled: 1 to enable, 0 to disable
        start_date: Ramadan start date (required if enabling)
        end_date: Ramadan end date (required if enabling)
    """
    frappe.only_for(["HR Manager", "System Manager"])

    settings = frappe.get_doc("Overtime Settings")
    settings.ramadan_mode_enabled = cint(enabled)

    if cint(enabled):
        if not start_date or not end_date:
            frappe.throw(_("Ramadan start and end dates are required when enabling Ramadan mode."))
        settings.ramadan_start_date = getdate(start_date)
        settings.ramadan_end_date = getdate(end_date)

        if settings.ramadan_start_date > settings.ramadan_end_date:
            frappe.throw(_("Ramadan start date cannot be after end date."))

    settings.save(ignore_permissions=True)
    frappe.db.commit()

    status = "enabled" if cint(enabled) else "disabled"
    frappe.msgprint(_(f"Ramadan mode {status}."))

    return {
        "ramadan_mode_enabled": cint(settings.ramadan_mode_enabled),
        "ramadan_start_date": str(settings.ramadan_start_date) if settings.ramadan_start_date else None,
        "ramadan_end_date": str(settings.ramadan_end_date) if settings.ramadan_end_date else None,
    }


@frappe.whitelist()
def get_overtime_dashboard_data(from_date=None, to_date=None):
    """
    Get dashboard summary data for overtime overview widgets.
    Returns KPIs, top employees, and daily trend data.

    Args:
        from_date: Start date (defaults to current month start)
        to_date: End date (defaults to today)

    Returns:
        dict with kpis, top_employees, daily_trend
    """
    from frappe.utils import get_first_day

    if not from_date:
        from_date = get_first_day(today())
    if not to_date:
        to_date = today()

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # KPI totals
    entries = frappe.get_all(
        "Overtime Entry",
        filters={
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": ["!=", 2],
        },
        fields=[
            "name", "employee", "employee_name", "department",
            "attendance_date", "overtime_hours", "overtime_rate_multiplier",
            "is_holiday_overtime", "status", "docstatus",
        ],
    )

    total_hours = sum(flt(e.overtime_hours) for e in entries)
    total_payable_hours = sum(
        flt(e.overtime_hours) * flt(e.overtime_rate_multiplier or 1)
        for e in entries
    )
    total_entries = len(entries)
    pending_count = len([e for e in entries if e.status == "Pending Approval"])
    approved_count = len([e for e in entries if e.status == "Approved"])
    submitted_count = len([e for e in entries if e.docstatus == 1])
    holiday_hours = sum(flt(e.overtime_hours) for e in entries if e.is_holiday_overtime)

    # Unique employees with overtime
    unique_employees = len(set(e.employee for e in entries))

    # Top 5 employees by hours
    emp_hours = {}
    for e in entries:
        emp_hours.setdefault(e.employee, {"employee": e.employee, "employee_name": e.employee_name, "department": e.department, "hours": 0})
        emp_hours[e.employee]["hours"] += flt(e.overtime_hours)

    top_employees = sorted(emp_hours.values(), key=lambda x: x["hours"], reverse=True)[:5]
    for emp in top_employees:
        emp["hours"] = round(emp["hours"], 2)

    # Daily trend
    daily = {}
    for e in entries:
        d = str(e.attendance_date)
        daily.setdefault(d, {"date": d, "hours": 0, "count": 0})
        daily[d]["hours"] += flt(e.overtime_hours)
        daily[d]["count"] += 1

    daily_trend = sorted(daily.values(), key=lambda x: x["date"])
    for day in daily_trend:
        day["hours"] = round(day["hours"], 2)

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "kpis": {
            "total_hours": round(total_hours, 2),
            "total_payable_hours": round(total_payable_hours, 2),
            "total_entries": total_entries,
            "pending_approval": pending_count,
            "approved": approved_count,
            "submitted": submitted_count,
            "holiday_overtime_hours": round(holiday_hours, 2),
            "unique_employees": unique_employees,
        },
        "top_employees": top_employees,
        "daily_trend": daily_trend,
    }
