// Copyright (c) 2026, Ali Raza and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.name) return;

		frm.add_custom_button(__("Overtime Summary"), function () {
			let today = frappe.datetime.get_today();
			let dt = frappe.datetime.str_to_obj(today);
			let month = dt.getMonth() + 1;
			let year = dt.getFullYear();

			frappe.call({
				method: "overtime.overtime.api.overtime.get_employee_overtime_details",
				args: {
					employee: frm.doc.name,
					month: month,
					year: year,
				},
				callback: function (r) {
					if (r.message) {
						let data = r.message;
						let msg = '<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px;">';
						let cards = [
							{ label: __("OT Hours"), value: data.total_overtime_hours || 0, color: "#2490ef" },
							{ label: __("Payable Hours"), value: data.total_payable_hours || 0, color: "#29cd42" },
							{ label: __("Entries"), value: data.total_entries || 0, color: "#7b68ee" },
						];
						cards.forEach(function (c) {
							msg +=
								'<div style="text-align: center; padding: 8px; border: 1px solid #d1d8dd; border-radius: 5px;">' +
								'<div style="font-size: 20px; font-weight: bold; color: ' + c.color + ';">' + c.value + "</div>" +
								'<div style="font-size: 11px; color: #8d99a6;">' + c.label + "</div></div>";
						});
						msg += "</div>";

						msg += __("Approved: {0} | Pending: {1} | Rejected: {2}", [
							data.approved_entries || 0,
							data.pending_entries || 0,
							data.rejected_entries || 0,
						]);

						if (data.entries && data.entries.length) {
							msg += '<hr><table class="table table-bordered table-sm" style="font-size: 11px; margin-top: 10px;">';
							msg += "<thead><tr><th>" + __("Date") + "</th><th>" + __("Hours") + "</th><th>" + __("Multiplier") + "</th><th>" + __("Status") + "</th></tr></thead><tbody>";
							data.entries.forEach(function (e) {
								let status_color = {
									"Approved": "green",
									"Rejected": "red",
									"Pending Approval": "orange",
									"Draft": "gray",
								}[e.status] || "gray";

								msg += "<tr>" +
									"<td>" + e.attendance_date + "</td>" +
									"<td>" + e.overtime_hours + "</td>" +
									"<td>" + e.overtime_rate_multiplier + "x</td>" +
									'<td><span style="color: ' + status_color + ';">' + e.status + "</span></td>" +
									"</tr>";
							});
							msg += "</tbody></table>";
						}

						frappe.msgprint({
							title: __("Overtime Summary - {0} ({1}/{2})", [frm.doc.employee_name, month, year]),
							message: msg,
							wide: true,
						});
					}
				},
			});
		}, __("Overtime"));

		frm.add_custom_button(__("Current Shift Info"), function () {
			frappe.call({
				method: "overtime.overtime.api.overtime.get_employee_shift_info",
				args: {
					employee: frm.doc.name,
				},
				callback: function (r) {
					if (r.message) {
						let info = r.message;
						let msg = "";
						msg += __("Date: {0}", [info.date]) + "<br>";
						msg += __("Employee Category: <b>{0}</b>", [info.employee_category]) + "<br>";
						msg += __("Default Shift: {0}", [info.default_shift || "-"]) + "<br>";
						msg += __("Active Shift: <b>{0}</b>", [info.active_shift || "-"]) + "<br>";

						if (info.shift_assignment) {
							msg += __("Shift Assignment: {0} (from {1})", [
								info.shift_assignment.name,
								info.shift_assignment.start_date,
							]) + "<br>";
						}

						if (info.is_ramadan) {
							msg += '<br><span style="color: green; font-weight: bold;">' + __("Ramadan Period Active") + "</span><br>";
						}

						if (info.applicable_rule) {
							let rule = info.applicable_rule;
							msg += "<br><b>" + __("Applicable Overtime Rule") + ":</b><br>";
							msg += __("Rule: {0}", [rule.name]) + "<br>";
							msg += __("Period: {0}", [rule.applicable_period]) + "<br>";
							msg += __("Timing: {0} - {1}", [rule.check_in_time, rule.check_out_time]) + "<br>";
							msg += __("Scheduled Hours: {0}h", [rule.total_shift_hours]) + "<br>";
							msg += __("OT Rate Multiplier: {0}x", [rule.overtime_rate_multiplier]) + "<br>";
							if (rule.is_overnight_shift) {
								msg += __("Overnight Shift: Yes") + "<br>";
							}
							if (rule.has_food_break) {
								msg += __("Food Break: {0} min ({1})", [rule.food_break_duration_minutes, rule.food_break_type]) + "<br>";
							}
						} else {
							msg += '<br><span style="color: orange;">' + __("No shift rule matched for today") + "</span>";
						}

						frappe.msgprint({
							title: __("Shift Info - {0}", [info.employee_name]),
							message: msg,
						});
					}
				},
			});
		}, __("Overtime"));

		frm.add_custom_button(__("View OT Entries"), function () {
			frappe.set_route("List", "Overtime Entry", {
				employee: frm.doc.name,
			});
		}, __("Overtime"));
	},
});
