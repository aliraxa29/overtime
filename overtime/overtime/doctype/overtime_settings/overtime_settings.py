# Copyright (c) 2026, Ali Raza and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate


class OvertimeSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        approval_role: DF.Link | None
        auto_create_overtime_entry: DF.Check
        default_overtime_rate_multiplier: DF.Float
        enabled: DF.Check
        holiday_overtime_rate_multiplier: DF.Float
        max_overtime_hours_per_day: DF.Float
        minimum_overtime_minutes: DF.Int
        overtime_based_on: DF.Literal["Shift Hours", "Fixed Daily Hours"]
        overtime_rounding: DF.Literal["No Rounding", "Round Up", "Round Down", "Round to Nearest"]
        ramadan_end_date: DF.Date | None
        ramadan_mode_enabled: DF.Check
        ramadan_start_date: DF.Date | None
        require_approval: DF.Check
        rounding_interval_minutes: DF.Int
    # end: auto-generated types
    
    
    def validate(self):
        self.validate_rounding()
        self.validate_ramadan_dates()
        self.validate_multipliers()
        self.validate_approval_role()

    def validate_approval_role(self):
        if cint(self.require_approval) and not self.approval_role:
            frappe.throw(_("Approval Role is required when Require Approval is enabled."))

    def validate_rounding(self):
        if self.overtime_rounding != "No Rounding":
            if cint(self.rounding_interval_minutes) <= 0:
                frappe.throw(_("Rounding interval must be greater than 0 when rounding is enabled."))

    def validate_ramadan_dates(self):
        if cint(self.ramadan_mode_enabled):
            if not self.ramadan_start_date or not self.ramadan_end_date:
                frappe.throw(_("Ramadan start and end dates are required when Ramadan mode is enabled."))
            if getdate(self.ramadan_start_date) >= getdate(self.ramadan_end_date):
                frappe.throw(_("Ramadan start date must be before end date."))

    def validate_multipliers(self):
        if flt(self.default_overtime_rate_multiplier) <= 0:
            frappe.throw(_("Default OT rate multiplier must be greater than 0."))
        if flt(self.holiday_overtime_rate_multiplier) <= 0:
            frappe.throw(_("Holiday OT rate multiplier must be greater than 0."))
