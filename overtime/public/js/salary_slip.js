// Copyright (c) 2026, Ali Raza and contributors
// For license information, please see license.txt

frappe.ui.form.on("Salary Slip", {
	refresh(frm) {
		if (!frm.doc.employee || !frm.doc.start_date || !frm.doc.end_date) return;

		if (frm.doc.overtime_hrs) {
			frm.dashboard.add_indicator(
				__("Overtime Hours: {0}h", [frm.doc.overtime_hrs]),
				"blue"
			);
		}

		frm.add_custom_button(__("Overtime Details"), function () {
			frappe.call({
				method: "overtime.overtime.api.overtime.get_overtime_summary",
				args: {
					employee: frm.doc.employee,
					from_date: frm.doc.start_date,
					to_date: frm.doc.end_date,
				},
				callback: function (r) {
					if (r.message) {
						let data = r.message;
						let msg = "";
						msg += __("Period: {0} to {1}", [frm.doc.start_date, frm.doc.end_date]) + "<br>";
						msg += __("Total OT Hours: <b>{0}</b>", [data.total_overtime_hours || 0]) + "<br>";
						msg += __("Total Payable Hours: <b>{0}</b>", [data.total_payable_hours || 0]) + "<br>";
						msg += __("Holiday OT Hours: {0}", [data.holiday_overtime_hours || 0]) + "<br>";
						msg += __("Submitted Entries: {0}", [data.total_entries || 0]) + "<br>";

						if (data.entries && data.entries.length) {
							msg += '<hr><table class="table table-bordered table-sm" style="font-size: 11px;">';
							msg += "<thead><tr><th>" + __("Date") + "</th><th>" + __("Shift") + "</th><th>" + __("OT Hrs") + "</th><th>" + __("Rate") + "</th><th>" + __("Payable") + "</th><th>" + __("Holiday") + "</th></tr></thead><tbody>";
							data.entries.forEach(function (e) {
								let payable = (e.overtime_hours * (e.overtime_rate_multiplier || 1)).toFixed(2);
								msg +=
									"<tr>" +
									"<td>" + e.attendance_date + "</td>" +
									"<td>" + (e.shift_type || "-") + "</td>" +
									"<td>" + e.overtime_hours + "</td>" +
									"<td>" + (e.overtime_rate_multiplier || 1) + "x</td>" +
									"<td>" + payable + "</td>" +
									"<td>" + (e.is_holiday_overtime ? "&#10003;" : "") + "</td>" +
									"</tr>";
							});
							msg += "</tbody></table>";
						}

						frappe.msgprint({
							title: __("Overtime Details - {0}", [frm.doc.employee_name || frm.doc.employee]),
							message: msg,
							wide: true,
						});
					}
				},
			});
		}, __("Overtime"));
	},
});
