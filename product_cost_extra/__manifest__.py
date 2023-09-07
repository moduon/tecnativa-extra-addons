# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Product Cost Extra",
    "summary": "Product cost extra amount",
    "version": "16.0.1.0.0",
    "development_status": "Production/Stable",
    "category": "Product",
    "website": "https://github.com/Tecnativa/extra-addons",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "product_cost_security",
        "stock_account",
    ],
    "data": [
        "security/product_cost_extra_security.xml",
        "views/product_pricelist_views.xml",
        "views/product_views.xml",
    ],
}
