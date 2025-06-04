# Copyright 2021 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "EDI Unilever Sale Product Set",
    "summary": "Extend sale_product_set for adjust to unilever",
    "version": "15.0.1.0.0",
    "development_status": "Beta",
    "category": "Product",
    "website": "https://github.com/OCA/sale-workflow",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["edi_backend_ulv", "sale_product_set"],
    "data": ["views/product_set.xml"],
    "application": False,
    "installable": True,
}
