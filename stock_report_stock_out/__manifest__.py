# Copyright 2019 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Stock report stock out",
    "summary": "Print report for products with stock out",
    "version": "16.0.1.0.0",
    "category": "Stock",
    "website": "https://github.com/Tecnativa/extra-addons",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["sale_stock"],
    "data": [
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "report/stock_report_stock_out_report.xml",  # Keep order
        "data/mail_template_data.xml",
        "views/report_stock_out_view.xml",
        "views/res_config_settings_views.xml",
        "wizard/stock_report_stock_out_view.xml",
    ],
}
