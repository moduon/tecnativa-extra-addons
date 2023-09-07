# Copyright 2021 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Purchase order line price list and margin",
    "summary": "Adds list price and margin fields on purchase order line",
    "version": "16.0.1.0.0",
    "category": "Stock",
    "website": "https://github.com/Tecnativa/extra-addons",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["product_cost_extra", "purchase"],
    "data": [
        "views/purchase_order_views.xml",
    ],
}
