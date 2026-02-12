# Copyright (c) 2026, Ali Raza and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate, today


def on_attendance_submit(doc, method=None):
    """
    Triggered when an Attendance record is submitted.
    Calculates overtime and creates an Overtime Entry if applicable.

    This is the primary integration point with HRMS.
    When Shift Type auto-attendance processes checkins and creates
    Attendance records, this hook fires and checks for overtime.
    """
    try:
        settings = frappe.get_cached_doc("Overtime Settings")
        if not settings.enabled:
            return

        if not settings.auto_create_overtime_entry:
            return

        # Only process Present or Half Day
        if doc.status not in ("Present", "Half Day"):
            return

        from overtime.overtime.utils import calculate_overtime_for_attendance

        ot_entry = calculate_overtime_for_attendance(doc.name)

        if ot_entry:
            # Update the custom fields on Attendance
            ot_doc = frappe.get_doc("Overtime Entry", ot_entry)
            doc.db_set("overtime_hours", ot_doc.overtime_hours, update_modified=False)
            doc.db_set("overtime_entry", ot_entry, update_modified=False)

            frappe.logger("overtime").info(
                f"Overtime Entry {ot_entry} created via hook for Attendance {doc.name} "
                f"(Employee: {doc.employee}, Date: {doc.attendance_date})"
            )

    except Exception as e:
        # Don't block attendance submission if overtime calculation fails
        frappe.log_error(
            f"Overtime calculation failed for Attendance {doc.name}: {str(e)}",
            "Overtime Hook Error",
        )


def on_attendance_cancel(doc, method=None):
    """
    Triggered when an Attendance record is cancelled.
    Cancels or deletes the linked Overtime Entry.
    """
    try:
        # Find linked overtime entries
        ot_entries = frappe.get_all(
            "Overtime Entry",
            filters={
                "attendance": doc.name,
                "docstatus": ["!=", 2],
            },
            pluck="name",
        )

        for ot_name in ot_entries:
            ot_doc = frappe.get_doc("Overtime Entry", ot_name)
            if ot_doc.docstatus == 1:
                # Cancel submitted entries
                ot_doc.cancel()
            elif ot_doc.docstatus == 0:
                # Delete draft entries
                frappe.delete_doc("Overtime Entry", ot_name, ignore_permissions=True)

            frappe.logger("overtime").info(
                f"Overtime Entry {ot_name} cancelled/deleted due to "
                f"Attendance {doc.name} cancellation"
            )

        # Clear custom fields on attendance
        doc.db_set("overtime_hours", 0, update_modified=False)
        doc.db_set("overtime_entry", None, update_modified=False)

    except Exception as e:
        frappe.log_error(
            f"Failed to cancel overtime for Attendance {doc.name}: {str(e)}",
            "Overtime Cancel Hook Error",
        )


def daily_overtime_processing():
    """
    Daily scheduled task to process overtime for the previous day.
    This is a fallback in case the on_submit hook missed anything
    (e.g. if overtime app was temporarily disabled or errored).

    Runs daily via scheduler_events in hooks.py.

    For overnight shifts: attendance_date is the shift start date,
    and this runs the day after, so yesterday's night shift attendance
    would have been processed already when the shift ended earlier today.
    """
    try:
        settings = frappe.get_cached_doc("Overtime Settings")
        if not settings.enabled:
            return

        from overtime.overtime.utils import process_overtime_for_date

        yesterday = add_days(getdate(today()), -1)
        count = process_overtime_for_date(date=yesterday)

        if count:
            frappe.logger("overtime").info(
                f"Daily overtime processing: {count} entries created for {yesterday}"
            )

    except Exception as e:
        frappe.log_error(
            f"Daily overtime processing failed: {str(e)}",
            "Overtime Scheduler Error",
        )


def on_salary_slip_validate(doc, method=None):
    """
    Triggered BEFORE Salary Slip validation (before_validate hook).

    Must run before HRMS's own validate() so that overtime_hrs
    is populated before formula/condition evaluation. HRMS evaluates
    salary component conditions (e.g. 'overtime_hrs > 0') during
    its validate() method, so this value must be set beforehand.

    overtime_hrs = SUM(overtime_hours * overtime_rate_multiplier)

    This value is then used by the Salary Component formula:
        ((base/30)/8) * overtime_hrs

    Since the multiplier (1.5x normal, 2.0x holiday) is already baked
    into overtime_hrs, the formula doesn't need a hardcoded rate.

    Example:
      Employee worked 2h normal OT (×1.5) + 3h holiday OT (×2.0)
      overtime_hrs = (2×1.5) + (3×2.0) = 3 + 6 = 9 payable hours
      OT amount = ((base/30)/8) * 9
    """
    try:
        from frappe.utils import flt

        if not doc.employee or not doc.start_date or not doc.end_date:
            return

        # Sum payable overtime hours from submitted Overtime Entries
        # overtime_hours × overtime_rate_multiplier for each entry
        result = frappe.db.sql(
            """
            SELECT
                COALESCE(SUM(overtime_hours * overtime_rate_multiplier), 0) as payable_hours,
                COALESCE(SUM(overtime_hours), 0) as raw_hours,
                COUNT(*) as entry_count
            FROM `tabOvertime Entry`
            WHERE employee = %s
              AND attendance_date BETWEEN %s AND %s
              AND docstatus = 1
            """,
            (doc.employee, doc.start_date, doc.end_date),
            as_dict=True,
        )

        payable_hours = flt(result[0].payable_hours, 2) if result else 0
        raw_hours = flt(result[0].raw_hours, 2) if result else 0
        entry_count = result[0].entry_count if result else 0

        doc.overtime_hrs = payable_hours

        if payable_hours > 0:
            frappe.logger("overtime").info(
                f"Salary Slip {doc.name}: {doc.employee} | "
                f"{entry_count} OT entries | {raw_hours}h raw | "
                f"{payable_hours}h payable (with multiplier)"
            )

    except Exception as e:
        # Don't block salary slip if overtime lookup fails
        frappe.log_error(
            f"Overtime hours lookup failed for Salary Slip {doc.name}: {str(e)}",
            "Overtime Salary Slip Hook Error",
        )
        doc.overtime_hrs = 0
