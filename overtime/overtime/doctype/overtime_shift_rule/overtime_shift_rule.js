// Copyright (c) 2026, Ali Raza and contributors
// For license information, please see license.txt

frappe.ui.form.on("Overtime Shift Rule", {
	refresh(frm) {
		if (frm.doc.check_in_time && frm.doc.check_out_time) {
			frm.trigger("compute_shift_hours_preview");
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__("Test Rule Match"), function () {
				frappe.prompt(
					{
						fieldname: "employee",
						label: __("Employee"),
						fieldtype: "Link",
						options: "Employee",
						reqd: 1,
					},
					function (values) {
						frappe.call({
							method: "overtime.overtime.api.overtime.get_employee_shift_info",
							args: {
								employee: values.employee,
								date: frappe.datetime.get_today(),
							},
							callback: function (r) {
								if (r.message) {
									let info = r.message;
									let matched_rule = info.applicable_rule;
									let msg = "";
									msg += __("Employee: {0} ({1})", [info.employee_name, info.employee]) + "<br>";
									msg += __("Category: {0}", [info.employee_category]) + "<br>";
									msg += __("Active Shift: {0}", [info.active_shift || "-"]) + "<br>";
									msg += __("Ramadan Active: {0}", [info.is_ramadan ? __("Yes") : __("No")]) + "<br><br>";

									if (matched_rule) {
										let is_this_rule = matched_rule.name === frm.doc.name;
										msg += '<b style="color: ' + (is_this_rule ? "green" : "orange") + ';">';
										msg += __("Matched Rule: {0}", [matched_rule.name]);
										msg += "</b><br>";
										if (!is_this_rule) {
											msg += __("(Different rule matched, not this one)");
										} else {
											msg += __("This rule matches the employee!");
										}
									} else {
										msg += '<b style="color: red;">' + __("No rule matched for this employee") + "</b>";
									}

									frappe.msgprint({ title: __("Rule Match Test"), message: msg });
								}
							},
						});
					},
					__("Test Employee Match"),
					__("Check")
				);
			});
		}
	},

	check_in_time(frm) {
		frm.trigger("compute_shift_hours_preview");
	},

	check_out_time(frm) {
		frm.trigger("compute_shift_hours_preview");
	},

	has_food_break(frm) {
		frm.trigger("compute_shift_hours_preview");
	},

	food_break_duration_minutes(frm) {
		frm.trigger("compute_shift_hours_preview");
	},

	food_break_included_in_shift(frm) {
		frm.trigger("compute_shift_hours_preview");
	},

	is_overnight_shift(frm) {
		frm.trigger("compute_shift_hours_preview");
	},

	compute_shift_hours_preview(frm) {
		if (!frm.doc.check_in_time || !frm.doc.check_out_time) return;

		let ci = moment(frm.doc.check_in_time, "HH:mm:ss");
		let co = moment(frm.doc.check_out_time, "HH:mm:ss");

		let diff_minutes = co.diff(ci, "minutes");
		if (diff_minutes <= 0 || frm.doc.is_overnight_shift) {
			// Overnight: add 24 hours
			diff_minutes = co.diff(ci, "minutes") + 24 * 60;
		}

		if (frm.doc.has_food_break && frm.doc.food_break_included_in_shift) {
			diff_minutes -= (frm.doc.food_break_duration_minutes || 0);
		}

		let total_hours = Math.max(0, diff_minutes / 60);
		frm.set_value("total_shift_hours", flt(total_hours, 2));
	},

	allow_late_early_exception(frm) {
		if (!frm.doc.allow_late_early_exception) {
			frm.set_value("late_early_grace_minutes", 0);
		}
	},

	overtime_eligible(frm) {
		if (!frm.doc.overtime_eligible) {
			frm.set_value("min_overtime_minutes", 0);
			frm.set_value("max_overtime_hours", 0);
			frm.set_value("overtime_rate_multiplier", 0);
		}
	},
});
