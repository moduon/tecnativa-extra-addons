# Copyright 2020 Tecnativa - Carlos Dauden
# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Agreement Unilever MEF",
    "summary": "Manage Unilever MEF agreements",
    "version": "15.0.1.0.0",
    "development_status": "Beta",
    "category": "Contract",
    "website": "https://github.com/OCA/contract",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["agreement", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/agreement_unilever_mef_data.xml",
        "data/agreement_unilever_mef_stock_data.xml",
        "data/report_paperformat_data.xml",
        "views/agreement_view.xml",
        "views/product_view.xml",
        "views/product_category_view.xml",
        "views/res_partner_view.xml",
        "views/stock_production_lot_views.xml",
        "report/agreement_unilever_mef_report.xml",
        # Respect file order
        "views/agreement_unilever_mef_menu.xml",
        "report/mef_report.xml",
        "report/mef_report_concession_templates.xml",
        "report/mef_report_recession_templates.xml",
    ],
}
