# Copyright 2022 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Stock Account Invoice Pending",
    "summary": "Add a report with purchase orders pending to invoice at date.",
    "version": "16.0.1.0.0",
    "author": "Tecnativa",
    "website": "https://github.com/Tecnativa/extra-addons",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "depends": [
        "purchase_stock",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/purchase_stock_account_invoice_pending_wizard_views.xml",
        "report/purchase_stock_invoice_pending_report.xml",
    ],
    "installable": True,
}
