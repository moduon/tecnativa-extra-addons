# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Sale stock deposit management",
    "summary": "Allow to sale and delivery products in deposit",
    "version": "13.0.1.0.0",
    "development_status": "Beta",
    "category": "Stock",
    "website": "https://gitlab.tecnativa.com/Tecnativa/marmenorda-odoo",
    "author": "Tecnativa",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "sale_stock",
        "stock_owner_restriction",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sale_stock_deposit_mgmt_data.xml",
        "views/res_partner_views.xml",
        "views/sale_stock_deposit_mgmt_menu.xml",
        "views/stock_picking_views.xml",
    ],
}
