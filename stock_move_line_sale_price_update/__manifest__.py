# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Stock Move Line Sale Price Update",
    "summary": "Update sale price from stock move lines",
    "version": "16.0.1.0.0",
    "development_status": "Beta",
    "category": "stock",
    "website": "https://github.com/Tecnativa/extra-addons",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "sale_stock",
        "stock_picking_batch_extended",
        "stock_picking_report_valued",
    ],
    "data": [
        "views/stock_move_line_views.xml",
        "views/stock_picking_batch_views.xml",
    ],
}
