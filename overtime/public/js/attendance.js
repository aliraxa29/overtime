// Copyright (c) 2026, Ali Raza and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		if (!frm.doc.employee || !frm.doc.attendance_date) return;

		frappe.call({
			method: "frappe.client.get_count",
			args: {
				doctype: "Overtime Entry",
				filters: {
					attendance: frm.doc.name,
					docstatus: ["!=", 2],
				},
			},
			callback: function (r) {
				if (r.message && r.message > 0) {
					frm.dashboard.add_indicator(
						__("Overtime Entry exists"),
						"green"
					);

					frm.add_custom_button(__("View Overtime Entry"), function () {
						frappe.set_route("List", "Overtime Entry", {
							attendance: frm.doc.name,
						});
					}, __("Overtime"));
				} else {
					frm.dashboard.add_indicator(
						__("No Overtime Entry"),
						"gray"
					);
				}
			},
		});

		frappe.call({
			method: "overtime.overtime.api.overtime.get_employee_shift_info",
			args: {
				employee: frm.doc.employee,
				date: frm.doc.attendance_date,
			},
			callback: function (r) {
				if (r.message) {
					let info = r.message;
					let html = '<div style="font-size: 12px; margin: 5px 0;">';
					html += "<b>" + __("Shift Rule") + ":</b> ";
					if (info.applicable_rule) {
						html += info.applicable_rule.shift_name;
						html += " (" + info.applicable_rule.total_shift_hours + "h";
						if (info.applicable_rule.is_overnight_shift) {
							html += ", " + __("Overnight");
						}
						html += ")";
					} else {
						html += __("None matched");
					}
					html += " &bull; <b>" + __("Category") + ":</b> " + info.employee_category;
					if (info.is_ramadan) {
						html += ' &bull; <span style="color: green; font-weight: bold;">' + __("Ramadan") + "</span>";
					}
					html += "</div>";
					frm.dashboard.add_section(html, __("Overtime Shift Info"));
					frm.dashboard.show();
				}
			},
		});

		frm.add_custom_button(__("Process Overtime"), function () {
			frappe.call({
				method: "overtime.overtime.utils.process_overtime_manually",
				args: {
					date: frm.doc.attendance_date,
					employee: frm.doc.employee,
				},
				freeze: true,
				freeze_message: __("Processing overtime..."),
				callback: function (r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __("Overtime processed for {0}", [frm.doc.employee_name || frm.doc.employee]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		}, __("Overtime"));

		frm.add_custom_button(__("Monthly Summary"), function () {
			let dt = frappe.datetime.str_to_obj(frm.doc.attendance_date);
			let month = dt.getMonth() + 1;
			let year = dt.getFullYear();

			frappe.call({
				method: "overtime.overtime.api.overtime.get_employee_overtime_details",
				args: {
					employee: frm.doc.employee,
					month: month,
					year: year,
				},
				callback: function (r) {
					if (r.message) {
						let data = r.message;
						let msg = "";
						msg += __("Period: {0}/{1}", [month, year]) + "<br>";
						msg += __("Total OT Hours: <b>{0}</b>", [data.total_overtime_hours || 0]) + "<br>";
						msg += __("Total Payable Hours: <b>{0}</b>", [data.total_payable_hours || 0]) + "<br>";
						msg += __("Total Entries: {0}", [data.total_entries || 0]) + "<br>";
						msg += __("Approved: {0} | Pending: {1} | Rejected: {2}", [
							data.approved_entries || 0,
							data.pending_entries || 0,
							data.rejected_entries || 0,
						]);
						frappe.msgprint({
							title: __("Overtime Summary - {0}", [frm.doc.employee_name || frm.doc.employee]),
							message: msg,
						});
					}
				},
			});
		}, __("Overtime"));
	},
});
