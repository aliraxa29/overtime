# Copyright (c) 2026, Ali Raza and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, today


class OvertimeEntry(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        actual_check_in: DF.Datetime | None
        actual_check_out: DF.Datetime | None
        actual_working_hours: DF.Float
        amended_from: DF.Link | None
        approval_date: DF.Date | None
        approved_by: DF.Link | None
        attendance: DF.Link | None
        attendance_date: DF.Date
        company: DF.Link | None
        department: DF.Link | None
        employee: DF.Link
        employee_name: DF.Data | None
        food_break_deducted: DF.Check
        food_break_minutes: DF.Int
        is_holiday_overtime: DF.Check
        overtime_hours: DF.Float
        overtime_minutes: DF.Float
        overtime_rate_multiplier: DF.Float
        overtime_shift_rule: DF.Link | None
        remarks: DF.SmallText | None
        scheduled_shift_hours: DF.Float
        shift_end_time: DF.Datetime | None
        shift_start_time: DF.Datetime | None
        shift_type: DF.Link | None
        status: DF.Literal["Draft", "Pending Approval", "Approved", "Rejected", "Cancelled"]
    # end: auto-generated types
    
    
    def validate(self):
        self.validate_duplicate()
        self.validate_overtime_hours()
        self.validate_dates()
        self.set_status_on_save()

    def before_submit(self):
        settings = frappe.get_cached_doc("Overtime Settings")
        if cint(settings.require_approval) and self.status not in ("Approved",):
            frappe.throw(
                _("Overtime Entry must be Approved before submission. Current status: {0}").format(
                    self.status
                )
            )
        if self.status == "Draft":
            self.status = "Approved"

    def on_submit(self):
        if not self.approved_by:
            self.db_set("approved_by", frappe.session.user)
        if not self.approval_date:
            self.db_set("approval_date", getdate(today()))

        # Update custom fields on linked Attendance
        if self.attendance:
            frappe.db.set_value(
                "Attendance", self.attendance,
                {
                    "overtime_hours": self.overtime_hours,
                    "overtime_entry": self.name,
                },
                update_modified=False,
            )

    def on_cancel(self):
        self.db_set("status", "Cancelled")

        # Clear custom fields on linked Attendance
        if self.attendance:
            frappe.db.set_value(
                "Attendance", self.attendance,
                {
                    "overtime_hours": 0,
                    "overtime_entry": None,
                },
                update_modified=False,
            )

    def validate_duplicate(self):
        """Check for duplicate overtime entry for same employee and date."""
        existing = frappe.db.exists(
            "Overtime Entry",
            {
                "employee": self.employee,
                "attendance_date": self.attendance_date,
                "docstatus": ["!=", 2],
                "name": ["!=", self.name],
            },
        )
        if existing:
            frappe.throw(
                _("Overtime Entry {0} already exists for {1} on {2}").format(
                    existing,
                    self.employee_name or self.employee,
                    self.attendance_date,
                )
            )

    def validate_overtime_hours(self):
        """Validate overtime hours are within reasonable limits."""
        if flt(self.overtime_hours) < 0:
            frappe.throw(_("Overtime hours cannot be negative."))

        if flt(self.overtime_hours) > 16:
            frappe.throw(_("Overtime hours cannot exceed 16 hours per day."))

        try:
            settings = frappe.get_cached_doc("Overtime Settings")
            max_ot = flt(settings.max_overtime_hours_per_day)
            if max_ot > 0 and flt(self.overtime_hours) > max_ot:
                frappe.msgprint(
                    _("Overtime hours ({0}) exceed the configured maximum ({1}h). Capping.").format(
                        self.overtime_hours, max_ot
                    ),
                    alert=True,
                )
                self.overtime_hours = max_ot
                self.overtime_minutes = max_ot * 60
        except Exception:
            pass

    def validate_dates(self):
        """Ensure attendance_date is not in the future."""
        if self.attendance_date and getdate(self.attendance_date) > getdate(today()):
            frappe.throw(_("Attendance date cannot be in the future."))

    def set_status_on_save(self):
        """Set status based on settings when saving as Draft."""
        if self.docstatus == 0 and self.status in ("Draft", None, ""):
            try:
                settings = frappe.get_cached_doc("Overtime Settings")
                if cint(settings.require_approval):
                    self.status = "Pending Approval"
                else:
                    self.status = "Approved"
            except Exception:
                self.status = "Draft"


def _check_approval_permission():
    """Check if current user has the configured approval role."""
    settings = frappe.get_cached_doc("Overtime Settings")
    if not cint(settings.require_approval):
        return

    approval_role = settings.approval_role
    if not approval_role:
        return

    user_roles = frappe.get_roles(frappe.session.user)
    if approval_role not in user_roles and "Administrator" not in user_roles:
        frappe.throw(
            _("You do not have the required role ({0}) to approve/reject overtime entries.").format(
                approval_role
            )
        )


@frappe.whitelist()
def approve_overtime(name):
    """Approve an overtime entry."""
    _check_approval_permission()

    doc = frappe.get_doc("Overtime Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("Only draft entries can be approved."))

    doc.status = "Approved"
    doc.approved_by = frappe.session.user
    doc.approval_date = getdate(today())
    doc.save(ignore_permissions=True)
    frappe.msgprint(_("Overtime Entry {0} approved.").format(name))
    return doc


@frappe.whitelist()
def reject_overtime(name, reason=None):
    """Reject an overtime entry."""
    _check_approval_permission()

    doc = frappe.get_doc("Overtime Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("Only draft entries can be rejected."))

    doc.status = "Rejected"
    if reason:
        doc.remarks = ((doc.remarks or "") + f"\nRejection Reason: {reason}").strip()
    doc.save(ignore_permissions=True)
    frappe.msgprint(_("Overtime Entry {0} rejected.").format(name))
    return doc
