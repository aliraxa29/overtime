frappe.listview_settings["Overtime Entry"] = {
    get_indicator: function(doc) {
        if (doc.status === 'Approved') {
            return [__('Approved'), 'green', 'status,=,Approved'];
        } else if (doc.status === 'Rejected') {
            return [__('Rejected'), 'red', 'status,=,Rejected'];
        } else if (doc.status === 'Pending Approval') {
            return [__('Pending Approval'), 'orange', 'status,=,Pending Approval'];
        } else if (doc.status === 'Cancelled') {
            return [__('Cancelled'), 'gray', 'status,=,Cancelled'];
        } else if (doc.status === 'Draft') {
            return [__('Draft'), 'gray', 'status,=,Draft'];
        }
    },

    onload: function(listview) {
        // ── Bulk Approve button ──
        listview.page.add_action_item(__("Bulk Approve"), function () {
            let selected = listview.get_checked_items();
            if (!selected.length) {
                frappe.msgprint(__("Please select entries to approve."));
                return;
            }
            let names = selected.map(function (d) { return d.name; });
            frappe.call({
                method: "overtime.overtime.api.overtime.bulk_approve_overtime",
                args: { entries: names },
                freeze: true,
                freeze_message: __("Approving {0} entries...", [names.length]),
                callback: function (r) {
                    if (!r.exc) {
                        listview.refresh();
                    }
                },
            });
        });

        // ── Bulk Reject button ──
        listview.page.add_action_item(__("Bulk Reject"), function () {
            let selected = listview.get_checked_items();
            if (!selected.length) {
                frappe.msgprint(__("Please select entries to reject."));
                return;
            }
            let names = selected.map(function (d) { return d.name; });
            frappe.prompt(
                {
                    fieldname: "reason",
                    label: __("Rejection Reason"),
                    fieldtype: "Small Text",
                },
                function (values) {
                    frappe.call({
                        method: "overtime.overtime.api.overtime.bulk_reject_overtime",
                        args: { entries: names, reason: values.reason },
                        freeze: true,
                        freeze_message: __("Rejecting {0} entries...", [names.length]),
                        callback: function (r) {
                            if (!r.exc) {
                                listview.refresh();
                            }
                        },
                    });
                },
                __("Bulk Reject Overtime"),
                __("Reject")
            );
        });

        // ── Bulk Submit button ──
        listview.page.add_action_item(__("Bulk Submit"), function () {
            let selected = listview.get_checked_items();
            if (!selected.length) {
                frappe.msgprint(__("Please select entries to submit."));
                return;
            }
            let names = selected.map(function (d) { return d.name; });
            frappe.confirm(
                __("Submit {0} overtime entries?", [names.length]),
                function () {
                    frappe.call({
                        method: "overtime.overtime.api.overtime.bulk_submit_overtime",
                        args: { entries: names },
                        freeze: true,
                        freeze_message: __("Submitting {0} entries...", [names.length]),
                        callback: function (r) {
                            if (!r.exc) {
                                listview.refresh();
                            }
                        },
                    });
                }
            );
        });
    },

    formatters: {
        overtime_hours: function (value) {
            if (value) {
                return '<b>' + value + 'h</b>';
            }
            return value;
        },
    },
}