// Copyright (c) 2026, Ali Raza and contributors
// For license information, please see license.txt

frappe.ui.form.on("Overtime Entry", {
	refresh(frm) {
		frm.page.set_indicator(frm.doc.status, {
			"Draft": "gray",
			"Pending Approval": "orange",
			"Approved": "blue",
			"Rejected": "red",
			"Cancelled": "gray",
		}[frm.doc.status] || "gray");

		if (frm.doc.docstatus === 0) {
			frappe.db.get_single_value("Overtime Settings", "approval_role").then((approval_role) => {
				let can_approve = false;
				if (approval_role) {
					can_approve = frappe.user_roles.includes(approval_role);
				}
				// Always allow System Manager / Administrator
				if (frappe.user_roles.includes("System Manager") || frappe.session.user === "Administrator") {
					can_approve = true;
				}

				if (frm.doc.status !== "Approved" && can_approve) {
					frm.add_custom_button(__("Approve"), function () {
						frappe.call({
							method: "overtime.overtime.doctype.overtime_entry.overtime_entry.approve_overtime",
							args: { name: frm.doc.name },
							freeze: true,
							freeze_message: __("Approving..."),
							callback: function (r) {
								if (!r.exc) {
									frm.reload_doc();
									frappe.show_alert({ message: __("Overtime Entry approved"), indicator: "green" });
								}
							},
						});
					}, __("Actions"));

					// Reject button
					frm.add_custom_button(__("Reject"), function () {
						frappe.prompt(
							{
								fieldname: "reason",
								label: __("Rejection Reason"),
								fieldtype: "Small Text",
								reqd: 1,
							},
							function (values) {
								frappe.call({
									method: "overtime.overtime.doctype.overtime_entry.overtime_entry.reject_overtime",
									args: { name: frm.doc.name, reason: values.reason },
									freeze: true,
									freeze_message: __("Rejecting..."),
									callback: function (r) {
										if (!r.exc) {
											frm.reload_doc();
											frappe.show_alert({ message: __("Overtime Entry rejected"), indicator: "red" });
										}
									},
								});
							},
							__("Reject Overtime"),
							__("Reject")
						);
					}, __("Actions"));
				}
			});

			// Recalculate button
			if (frm.doc.employee && frm.doc.attendance_date) {
				frm.add_custom_button(__("Recalculate"), function () {
					frappe.call({
						method: "overtime.overtime.api.overtime.recalculate_overtime",
						args: {
							employee: frm.doc.employee,
							from_date: frm.doc.attendance_date,
							to_date: frm.doc.attendance_date,
						},
						freeze: true,
						freeze_message: __("Recalculating..."),
						callback: function (r) {
							if (!r.exc) {
								frm.reload_doc();
								frappe.show_alert({ message: __("Overtime recalculated"), indicator: "green" });
							}
						},
					});
				}, __("Actions"));
			}
		}

		if (frm.doc.employee && frm.doc.attendance_date && !frm.is_new()) {
			let payable = ((frm.doc.overtime_hours || 0) * (frm.doc.overtime_rate_multiplier || 1)).toFixed(2);
			let is_holiday = frm.doc.is_holiday_overtime ? __("Yes") : __("No");
			let html = '<div class="row" style="margin: 5px 0; font-size: 12px;">'
				+ '<div class="col-sm-2"><b>' + __("Shift") + '</b><br>' + (frm.doc.shift_type || "-") + '</div>'
				+ '<div class="col-sm-2"><b>' + __("Scheduled") + '</b><br>' + (frm.doc.scheduled_shift_hours || 0) + 'h</div>'
				+ '<div class="col-sm-2"><b>' + __("Actual") + '</b><br>' + (frm.doc.actual_working_hours || 0) + 'h</div>'
				+ '<div class="col-sm-2"><b>' + __("Overtime") + '</b><br><span style="color:#2490ef; font-weight:bold;">' + (frm.doc.overtime_hours || 0) + 'h</span></div>'
				+ '<div class="col-sm-2"><b>' + __("Payable") + '</b><br><span style="color:#29cd42; font-weight:bold;">' + payable + 'h</span> (' + (frm.doc.overtime_rate_multiplier || 1) + 'x)</div>'
				+ '<div class="col-sm-2"><b>' + __("Holiday OT") + '</b><br>' + is_holiday + '</div>'
				+ '</div>';
			frm.dashboard.add_section(html, __("Overtime Summary"));
			frm.dashboard.show();
		}
	},

	employee(frm) {
		if (frm.doc.employee && frm.doc.attendance_date) {
			frm.trigger("fetch_shift_info");
		}
	},

	attendance_date(frm) {
		if (frm.doc.employee && frm.doc.attendance_date) {
			frm.trigger("fetch_shift_info");
		}
	},

	fetch_shift_info(frm) {
		frappe.call({
			method: "overtime.overtime.api.overtime.get_employee_shift_info",
			args: {
				employee: frm.doc.employee,
				date: frm.doc.attendance_date,
			},
			callback: function (r) {
				if (r.message) {
					let info = r.message;
					let msg_parts = [];
					msg_parts.push(__("Employee Category: {0}", [info.employee_category]));
					msg_parts.push(__("Active Shift: {0}", [info.active_shift || "-"]));
					if (info.is_ramadan) {
						msg_parts.push('<span style="color: green; font-weight: bold;">' + __("Ramadan Period Active") + "</span>");
					}
					if (info.applicable_rule) {
						msg_parts.push(__("Shift Rule: {0}", [info.applicable_rule.name]));
						msg_parts.push(__("Scheduled Hours: {0}", [info.applicable_rule.total_shift_hours]));
					}
					frm.dashboard.add_comment(msg_parts.join(" &bull; "), "blue", true);
				}
			},
		});
	},
});
