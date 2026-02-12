// Copyright (c) 2026, Ali Raza and contributors
// For license information, please see license.txt

frappe.ui.form.on("Overtime Settings", {
	refresh(frm) {
		if (frm.doc.ramadan_mode_enabled) {
			frm.add_custom_button(__("Disable Ramadan Mode"), function () {
				frappe.call({
					method: "overtime.overtime.api.overtime.toggle_ramadan_mode",
					args: { enabled: 0 },
					freeze: true,
					freeze_message: __("Disabling Ramadan Mode..."),
					callback: function (r) {
						if (!r.exc) {
							frm.reload_doc();
							frappe.show_alert({ message: __("Ramadan Mode disabled"), indicator: "orange" });
						}
					},
				});
			}, __("Ramadan"));
		} else {
			frm.add_custom_button(__("Enable Ramadan Mode"), function () {
				let today = frappe.datetime.get_today();
				frappe.prompt(
					[
						{
							fieldname: "start_date",
							label: __("Ramadan Start Date"),
							fieldtype: "Date",
							reqd: 1,
							default: today,
						},
						{
							fieldname: "end_date",
							label: __("Ramadan End Date"),
							fieldtype: "Date",
							reqd: 1,
							default: frappe.datetime.add_days(today, 29),
						},
					],
					function (values) {
						frappe.call({
							method: "overtime.overtime.api.overtime.toggle_ramadan_mode",
							args: {
								enabled: 1,
								start_date: values.start_date,
								end_date: values.end_date,
							},
							freeze: true,
							freeze_message: __("Enabling Ramadan Mode..."),
							callback: function (r) {
								if (!r.exc) {
									frm.reload_doc();
									frappe.show_alert({ message: __("Ramadan Mode enabled"), indicator: "green" });
								}
							},
						});
					},
					__("Set Ramadan Period"),
					__("Enable")
				);
			}, __("Ramadan"));
		}

		frm.add_custom_button(__("Check Today"), function () {
			frappe.call({
				method: "overtime.overtime.api.overtime.check_ramadan_status",
				callback: function (r) {
					if (r.message) {
						let data = r.message;
						let msg = __("Date: {0}", [data.date]) + "<br>";
						msg += __("Ramadan Mode: {0}", [data.ramadan_mode_enabled ? __("Enabled") : __("Disabled")]) + "<br>";
						if (data.ramadan_mode_enabled) {
							msg += __("Period: {0} to {1}", [data.ramadan_start_date, data.ramadan_end_date]) + "<br>";
							msg += __("Today is {0}in Ramadan period", [data.is_ramadan ? "" : __("NOT ")]);
						}
						frappe.msgprint({ title: __("Ramadan Status"), message: msg, indicator: data.is_ramadan ? "green" : "blue" });
					}
				},
			});
		}, __("Ramadan"));

		frm.add_custom_button(__("View Shift Rules"), function () {
			frappe.call({
				method: "overtime.overtime.api.overtime.get_all_shift_rules",
				args: { enabled_only: 1 },
				callback: function (r) {
					if (r.message && r.message.length) {
						let msg = '<table class="table table-bordered table-sm" style="font-size: 12px;">';
						msg += "<thead><tr><th>" + __("Shift") + "</th><th>" + __("Period") + "</th><th>" + __("Category") + "</th><th>" + __("Time") + "</th><th>" + __("Hours") + "</th><th>" + __("OT Rate") + "</th></tr></thead><tbody>";
						r.message.forEach(function (rule) {
							msg +=
								"<tr>" +
								"<td>" + rule.shift_name + "</td>" +
								"<td>" + rule.applicable_period + "</td>" +
								"<td>" + rule.employee_category + "</td>" +
								"<td>" + rule.check_in_time + " - " + rule.check_out_time + "</td>" +
								"<td>" + rule.total_shift_hours + "</td>" +
								"<td>" + rule.overtime_rate_multiplier + "x</td>" +
								"</tr>";
						});
						msg += "</tbody></table>";
						frappe.msgprint({ title: __("Active Shift Rules ({0})", [r.message.length]), message: msg, wide: true });
					} else {
						frappe.msgprint(__("No shift rules found."));
					}
				},
			});
		});

		frm.add_custom_button(__("Overtime Dashboard"), function () {
			frappe.call({
				method: "overtime.overtime.api.overtime.get_overtime_dashboard_data",
				freeze: true,
				callback: function (r) {
					if (r.message) {
						let d = r.message;
						let kpi = d.kpis;
						let msg = '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px;">';
						let cards = [
							{ label: __("Total Hours"), value: kpi.total_hours, color: "#2490ef" },
							{ label: __("Payable Hours"), value: kpi.total_payable_hours, color: "#29cd42" },
							{ label: __("Pending"), value: kpi.pending_approval, color: "#ffa00a" },
							{ label: __("Employees"), value: kpi.unique_employees, color: "#7b68ee" },
						];
						cards.forEach(function (c) {
							msg +=
								'<div style="text-align: center; padding: 10px; border: 1px solid #d1d8dd; border-radius: 5px;">' +
								'<div style="font-size: 22px; font-weight: bold; color: ' + c.color + ';">' + c.value + "</div>" +
								'<div style="font-size: 11px; color: #8d99a6;">' + c.label + "</div></div>";
						});
						msg += "</div>";

						if (d.top_employees && d.top_employees.length) {
							msg += "<h6>" + __("Top Employees (by OT Hours)") + "</h6>";
							msg += '<table class="table table-bordered table-sm" style="font-size: 12px;">';
							msg += "<thead><tr><th>" + __("Employee") + "</th><th>" + __("Department") + "</th><th>" + __("Hours") + "</th></tr></thead><tbody>";
							d.top_employees.forEach(function (e) {
								msg += "<tr><td>" + e.employee_name + "</td><td>" + (e.department || "-") + "</td><td>" + e.hours + "</td></tr>";
							});
							msg += "</tbody></table>";
						}

						frappe.msgprint({
							title: __("Overtime Dashboard ({0} to {1})", [d.from_date, d.to_date]),
							message: msg,
							wide: true,
						});
					}
				},
			});
		});
	},

	ramadan_mode_enabled(frm) {
		// Show/hide Ramadan date fields dynamically
		if (!frm.doc.ramadan_mode_enabled) {
			frm.set_value("ramadan_start_date", null);
			frm.set_value("ramadan_end_date", null);
		}
	},

	ramadan_end_date(frm) {
		// Validate end > start
		if (frm.doc.ramadan_start_date && frm.doc.ramadan_end_date) {
			if (frm.doc.ramadan_end_date < frm.doc.ramadan_start_date) {
				frappe.msgprint(__("Ramadan end date cannot be before start date."));
				frm.set_value("ramadan_end_date", null);
			}
		}
	},
});
