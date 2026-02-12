# Copyright (c) 2026, Ali Raza and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
    "Employee": [
        {
            "fieldname": "religion_category",
            "fieldtype": "Select",
            "label": "Religion Category",
            "options": "\nMuslim\nNon-Muslim",
            "insert_after": "gender",
            "description": "To determine applicable shift rules during Ramadan",
        },
    ],
    "Attendance": [
        {
            "fieldname": "overtime_hours",
            "fieldtype": "Float",
            "label": "Overtime Hours",
            "precision": "2",
            "insert_after": "working_hours",
            "read_only": 1,
            "description": "Overtime hours calculated by Overtime app",
        },
        {
            "fieldname": "overtime_entry",
            "fieldtype": "Link",
            "label": "Overtime Entry",
            "options": "Overtime Entry",
            "insert_after": "overtime_hours",
            "read_only": 1,
        },
    ],
    "Salary Slip": [
        {
            "fieldname": "overtime_hrs",
            "fieldtype": "Float",
            "label": "Overtime Hours",
            "precision": "2",
            "insert_after": "total_working_hours",
            "read_only": 1,
            "description": "Total payable overtime hours (hours × rate multiplier) from submitted Overtime Entries. Populated automatically during salary slip processing.",
        },
    ],
}


def after_install():
    """Run after app installation."""
    create_custom_fields(CUSTOM_FIELDS, update=True)
    create_overtime_salary_component()
    create_default_shift_types()
    create_default_shift_rules()
    frappe.db.commit()


def create_overtime_salary_component():
    """Create the 'Overtime' Salary Component if it doesn't exist.

    Formula: ((base/30)/8) * overtime_hrs
      - base/30      = daily rate
      - /8           = hourly rate (8-hour standard day)
      - overtime_hrs = sum of (overtime_hours × rate_multiplier)
                              already includes 1.5x or 2.0x multiplier

    The condition `overtime_hrs > 0` ensures the component
    only appears when there is overtime to pay.
    """
    if frappe.db.exists("Salary Component", "Overtime"):
        return

    sc = frappe.new_doc("Salary Component")
    sc.salary_component = "Overtime"
    sc.salary_component_abbr = "OT"
    sc.type = "Earning"
    sc.depends_on_payment_days = 0
    sc.is_tax_applicable = 0
    sc.remove_if_zero_valued = 1
    sc.amount_based_on_formula = 1
    sc.formula = "((base/30)/8) * overtime_hrs"
    sc.condition = "overtime_hrs > 0"
    sc.description = (
        "Overtime earnings calculated from approved Overtime Entries. "
        "overtime_hrs includes the rate multiplier (1.5x normal, 2.0x holiday)."
    )
    sc.insert(ignore_permissions=True)


def create_default_shift_types():
    """
    Create/update HRMS Shift Types to match the company shift schedule.

    Standard Shifts (all employees, year-round):
      - Morning:  7:30 AM - 3:30 PM  (8h), ±15 min grace, 30 min food break
      - Evening:  3:30 PM - 11:30 PM (8h), ±15 min grace, 30 min food break
      - Night:   11:30 PM - 7:30 AM  (8h, overnight), ±15 min grace, 30 min food break

    Ramadan Shifts (assigned during Ramadan via Shift Assignment):
      - Ramadan Morning - Factory (Muslim):   7:00 AM - 1:00 PM  (6h), no grace, no break
      - Ramadan Morning - Admin (Muslim):     9:00 AM - 3:00 PM  (6h), no grace, no break
      - Ramadan Night - Factory (Muslim):    12:00 AM - 7:30 AM  (7.5h), no grace, 1h suhoor
      - Ramadan Evening - Factory (Non-Muslim): 4:00 PM - 12:00 AM (8h, overnight), no grace, 30 min break

    Non-Muslim employees use standard shift types during Ramadan (unchanged timing).
    """
    shift_types = [
        # Standard
        {"name": "Morning", "start_time": "07:30:00", "end_time": "15:30:00", "grace": 15},
        {"name": "Evening", "start_time": "15:30:00", "end_time": "23:30:00", "grace": 15},
        {"name": "Night", "start_time": "23:30:00", "end_time": "07:30:00", "grace": 15},
        # Ramadan
        {"name": "Ramadan Morning - Factory (Muslim)", "start_time": "07:00:00", "end_time": "13:00:00", "grace": 0},
        {"name": "Ramadan Morning - Admin (Muslim)", "start_time": "09:00:00", "end_time": "15:00:00", "grace": 0},
        {"name": "Ramadan Night - Factory (Muslim)", "start_time": "00:00:00", "end_time": "07:30:00", "grace": 0},
        {"name": "Ramadan Evening - Factory (Non-Muslim)", "start_time": "16:00:00", "end_time": "00:00:00", "grace": 0},
    ]

    for sh in shift_types:
        if frappe.db.exists("Shift Type", sh["name"]):
            doc = frappe.get_doc("Shift Type", sh["name"])
            doc.start_time = sh["start_time"]
            doc.end_time = sh["end_time"]
            doc.late_entry_grace_period = sh["grace"]
            doc.early_exit_grace_period = sh["grace"]
            doc.save(ignore_permissions=True)
        else:
            doc = frappe.new_doc("Shift Type")
            doc.__newname = sh["name"]
            doc.start_time = sh["start_time"]
            doc.end_time = sh["end_time"]
            doc.enable_auto_attendance = 1
            doc.late_entry_grace_period = sh["grace"]
            doc.early_exit_grace_period = sh["grace"]
            doc.begin_check_in_before_shift_start_time = 60
            doc.allow_check_out_after_shift_end_time = 120
            doc.insert(ignore_permissions=True)


def create_default_shift_rules():
    """
    Create default Overtime Shift Rules matching the company shift schedule.

    Each rule links to an HRMS Shift Type and defines:
      - Standard working hours (for overtime calculation)
      - Food break deductions
      - Late/early grace periods
      - Overtime eligibility and rate multipliers

    Standard Shifts (all employees, year-round):
      - Morning:  7:30 AM - 3:30 PM → 7.5h net (30 min break excluded), ±15 min grace
      - Evening:  3:30 PM - 11:30 PM → 7.5h net (30 min break excluded), ±15 min grace
      - Night:   11:30 PM - 7:30 AM → 7.5h net (30 min break excluded), ±15 min grace [OVERNIGHT]

    Ramadan Shifts (Muslim Employees):
      - Factory Morning:  7:00 AM - 1:00 PM → 6.0h, no grace, no break
      - Admin Morning:    9:00 AM - 3:00 PM → 6.0h, no grace, no break
      - Factory Night:   12:00 AM - 7:30 AM → 6.5h net (1h suhoor break excluded)

    Ramadan Shifts (Non-Muslim Employees):
      - Factory Evening:  4:00 PM - 12:00 AM → 7.5h net (30 min break excluded) [OVERNIGHT]
    """
    shift_rules = [
        # ===== STANDARD SHIFTS (All employees) =====
        {
            "shift_name": "Morning",
            "shift_type": "Morning",
            "applicable_period": "Standard",
            "employee_category": "All",
            "check_in_time": "07:30:00",
            "check_out_time": "15:30:00",
            "is_overnight_shift": 0,
            "allow_late_early_exception": 1,
            "late_early_grace_minutes": 15,
            "has_food_break": 1,
            "food_break_duration_minutes": 30,
            "food_break_type": "Regular Break",
            "food_break_included_in_shift": 1,
            "overtime_eligible": 1,
            "min_overtime_minutes": 15,
            "max_overtime_hours": 4.0,
            "overtime_rate_multiplier": 1.0,
            "notes": "Standard morning shift 7:30AM-3:30PM. 30 min food break excluded. ±15 min grace.",
        },
        {
            "shift_name": "Evening",
            "shift_type": "Evening",
            "applicable_period": "Standard",
            "employee_category": "All",
            "check_in_time": "15:30:00",
            "check_out_time": "23:30:00",
            "is_overnight_shift": 0,
            "allow_late_early_exception": 1,
            "late_early_grace_minutes": 15,
            "has_food_break": 1,
            "food_break_duration_minutes": 30,
            "food_break_type": "Regular Break",
            "food_break_included_in_shift": 1,
            "overtime_eligible": 1,
            "min_overtime_minutes": 15,
            "max_overtime_hours": 4.0,
            "overtime_rate_multiplier": 1.0,
            "notes": "Standard evening shift 3:30PM-11:30PM. 30 min food break excluded. ±15 min grace.",
        },
        {
            "shift_name": "Night",
            "shift_type": "Night",
            "applicable_period": "Standard",
            "employee_category": "All",
            "check_in_time": "23:30:00",
            "check_out_time": "07:30:00",
            "is_overnight_shift": 1,
            "allow_late_early_exception": 1,
            "late_early_grace_minutes": 15,
            "has_food_break": 1,
            "food_break_duration_minutes": 30,
            "food_break_type": "Regular Break",
            "food_break_included_in_shift": 1,
            "overtime_eligible": 1,
            "min_overtime_minutes": 15,
            "max_overtime_hours": 4.0,
            "overtime_rate_multiplier": 1.0,
            "notes": "Standard night shift 11:30PM-7:30AM (overnight). 30 min food break excluded. ±15 min grace.",
        },
        # ===== RAMADAN SHIFTS (Muslim Employees) =====
        {
            "shift_name": "Factory Staff - Morning (Muslim Employees)",
            "shift_type": "Ramadan Morning - Factory (Muslim)",
            "applicable_period": "Ramadan",
            "employee_category": "Muslim",
            "check_in_time": "07:00:00",
            "check_out_time": "13:00:00",
            "is_overnight_shift": 0,
            "allow_late_early_exception": 0,
            "late_early_grace_minutes": 0,
            "has_food_break": 0,
            "food_break_duration_minutes": 0,
            "food_break_type": "Regular Break",
            "food_break_included_in_shift": 0,
            "overtime_eligible": 1,
            "min_overtime_minutes": 15,
            "max_overtime_hours": 4.0,
            "overtime_rate_multiplier": 1.0,
            "notes": "Ramadan morning shift for Muslim factory staff. 7:00AM-1:00PM (6h). No break. No grace.",
        },
        {
            "shift_name": "Admin Staff - Morning (Muslim Employees)",
            "shift_type": "Ramadan Morning - Admin (Muslim)",
            "applicable_period": "Ramadan",
            "employee_category": "Muslim",
            "check_in_time": "09:00:00",
            "check_out_time": "15:00:00",
            "is_overnight_shift": 0,
            "allow_late_early_exception": 0,
            "late_early_grace_minutes": 0,
            "has_food_break": 0,
            "food_break_duration_minutes": 0,
            "food_break_type": "Regular Break",
            "food_break_included_in_shift": 0,
            "overtime_eligible": 1,
            "min_overtime_minutes": 15,
            "max_overtime_hours": 4.0,
            "overtime_rate_multiplier": 1.0,
            "notes": "Ramadan morning shift for Muslim admin staff. 9:00AM-3:00PM (6h). No break. No grace.",
        },
        {
            "shift_name": "Factory Staff - Night (Muslim Employees)",
            "shift_type": "Ramadan Night - Factory (Muslim)",
            "applicable_period": "Ramadan",
            "employee_category": "Muslim",
            "check_in_time": "00:00:00",
            "check_out_time": "07:30:00",
            "is_overnight_shift": 0,
            "allow_late_early_exception": 0,
            "late_early_grace_minutes": 0,
            "has_food_break": 1,
            "food_break_duration_minutes": 60,
            "food_break_type": "Suhoor Break",
            "food_break_included_in_shift": 1,
            "overtime_eligible": 1,
            "min_overtime_minutes": 15,
            "max_overtime_hours": 4.0,
            "overtime_rate_multiplier": 1.0,
            "notes": "Ramadan night shift for Muslim factory staff. 12:00AM-7:30AM (7.5h, 6.5h net after 1h suhoor). No grace.",
        },
        # ===== RAMADAN SHIFTS (Non-Muslim Employees) =====
        {
            "shift_name": "Factory Staff - Evening (Non-Muslim Employees)",
            "shift_type": "Ramadan Evening - Factory (Non-Muslim)",
            "applicable_period": "Ramadan",
            "employee_category": "Non-Muslim",
            "check_in_time": "16:00:00",
            "check_out_time": "00:00:00",
            "is_overnight_shift": 1,
            "allow_late_early_exception": 0,
            "late_early_grace_minutes": 0,
            "has_food_break": 1,
            "food_break_duration_minutes": 30,
            "food_break_type": "Regular Break",
            "food_break_included_in_shift": 1,
            "overtime_eligible": 1,
            "min_overtime_minutes": 15,
            "max_overtime_hours": 4.0,
            "overtime_rate_multiplier": 1.0,
            "notes": "Ramadan evening shift for Non-Muslim factory staff. 4:00PM-12:00AM (8h, 7.5h net). No grace.",
        },
    ]

    for rule_data in shift_rules:
        rule_name = f"{rule_data['shift_name']}-{rule_data['employee_category']}-{rule_data['applicable_period']}"
        if frappe.db.exists("Overtime Shift Rule", rule_name):
            continue

        rule = frappe.new_doc("Overtime Shift Rule")
        rule.update(rule_data)
        rule.enabled = 1
        rule.insert(ignore_permissions=True)
