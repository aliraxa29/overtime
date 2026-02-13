# Copyright (c) 2026, Ali Raza and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_time, getdate, today


class OvertimeShiftRule(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        allow_late_early_exception: DF.Check
        applicable_period: DF.Literal["Standard", "Ramadan"]
        check_in_time: DF.Time
        check_out_time: DF.Time
        department: DF.Link | None
        employee_category: DF.Literal["All", "Muslim", "Non-Muslim"]
        enabled: DF.Check
        food_break_duration_minutes: DF.Int
        food_break_included_in_shift: DF.Check
        food_break_type: DF.Literal["Regular Break", "Suhoor Break", "Iftar Break"]
        has_food_break: DF.Check
        is_overnight_shift: DF.Check
        late_early_grace_minutes: DF.Int
        max_overtime_hours: DF.Float
        min_overtime_minutes: DF.Int
        notes: DF.SmallText | None
        overtime_eligible: DF.Check
        overtime_rate_multiplier: DF.Float
        shift_name: DF.Data
        shift_type: DF.Link | None
        total_shift_hours: DF.Float
    # end: auto-generated types
    
    
    def validate(self):
        self.calculate_total_shift_hours()
        self.validate_times()

    def calculate_total_shift_hours(self):
        """
        Calculate total shift hours from check-in/check-out times.

        For overnight shifts (is_overnight_shift=1 or check_out <= check_in),
        adds 24 hours to make the duration positive.

        If food break is excluded from shift hours, deducts that too.
        """
        check_in = get_time(self.check_in_time)
        check_out = get_time(self.check_out_time)

        from datetime import datetime, timedelta

        base_date = datetime(2026, 1, 1)
        dt_in = datetime.combine(base_date, check_in)
        dt_out = datetime.combine(base_date, check_out)

        # Handle overnight shifts (e.g. 23:30 -> 07:30)
        if cint(self.is_overnight_shift) or dt_out <= dt_in:
            dt_out += timedelta(days=1)

        total_minutes = (dt_out - dt_in).total_seconds() / 60

        # Deduct food break if excluded from shift hours
        if cint(self.has_food_break) and cint(self.food_break_included_in_shift):
            total_minutes -= cint(self.food_break_duration_minutes) or 0

        self.total_shift_hours = round(total_minutes / 60, 2)

    def validate_times(self):
        if self.total_shift_hours <= 0:
            frappe.throw(
                _("Total shift hours must be greater than 0. Check your check-in/check-out times and food break settings.")
            )

        if self.total_shift_hours > 24:
            frappe.throw(_("Total shift hours cannot exceed 24 hours."))


def get_applicable_shift_rule(employee, shift_type=None, date=None):
    """
    Get the most applicable Overtime Shift Rule for an employee.

    Matching priority (scored):
      +100  Period match (Ramadan rule in Ramadan, Standard in non-Ramadan)
      +50   Employee category match (Muslim/Non-Muslim)
      +30   Shift type match
      +25   Department match
      +10   Fallback (Standard in Ramadan, or category=All)

    Excluded:
      - Ramadan rules during non-Ramadan period
      - Wrong employee category (unless All)
      - Wrong department (if rule has department set)
    """
    if not date:
        date = getdate(today())
    else:
        date = getdate(date)

    # Check if we're in Ramadan period
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

    # Get employee's religion category and department
    employee_category = get_employee_category(employee)
    department = frappe.db.get_value("Employee", employee, "department")

    # Build filters
    filters = {"enabled": 1}
    if shift_type:
        # Include rules matching this shift_type OR rules with no shift_type set (generic)
        pass  # We'll filter in scoring below

    # Fetch all enabled rules
    rules = frappe.get_all(
        "Overtime Shift Rule",
        filters=filters,
        fields=["*"],
        order_by="creation desc",
    )

    if not rules:
        return None

    # Score and rank rules for best match
    best_rule = None
    best_score = -1

    for rule in rules:
        score = 0

        # ----- Period matching -----
        if is_ramadan and rule.applicable_period == "Ramadan":
            score += 100
        elif not is_ramadan and rule.applicable_period == "Standard":
            score += 100
        elif is_ramadan and rule.applicable_period == "Standard":
            score += 10  # Fallback: standard rule during Ramadan
        else:
            continue  # Skip Ramadan rules during non-Ramadan period

        # ----- Employee category matching -----
        if rule.employee_category == employee_category:
            score += 50
        elif rule.employee_category == "All":
            score += 10
        else:
            continue  # Wrong category, skip

        # ----- Department matching -----
        if rule.department:
            if department and rule.department == department:
                score += 25
            else:
                continue  # Wrong department, skip

        # ----- Shift type matching -----
        if rule.shift_type:
            if shift_type and rule.shift_type == shift_type:
                score += 30
            else:
                continue  # Wrong shift type, skip

        if score > best_score:
            best_score = score
            best_rule = rule

    return best_rule


def get_employee_category(employee):
    """
    Determine employee category (Muslim/Non-Muslim/All).

    Reads Employee.religion_category (custom field
    created by this app during installation via setup.py).

    Returns:
      'Muslim', 'Non-Muslim', or 'All' as fallback
    """
    category = frappe.db.get_value(
        "Employee", employee, "religion_category"
    ) or ""

    if category:
        cat_lower = category.lower().strip()
        if cat_lower in ("islam", "muslim"):
            return "Muslim"
        elif cat_lower in ("non-muslim", "non muslim"):
            return "Non-Muslim"
        return category  # Return as-is if it's already a valid option

    return "All"
