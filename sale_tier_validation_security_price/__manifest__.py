# Copyright 2021 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Sale Tier Validation Security Price",
    "summary": "Client customizations",
    "version": "16.0.1.0.0",
    "development_status": "Beta",
    "category": "Sale",
    "website": "https://github.com/Tecnativa/extra-addons",
    "author": "Tecnativa",
    "license": "AGPL-3",
    "application": False,
    "installable": False,
    "depends": [
        "base_tier_validation_formula",
        "sale_tier_validation",
        "sale_product_security_price",
    ],
    "data": [
        "data/sale_tier_validation_custom_data.xml",
        "views/sale_order_view.xml",
        "views/sale_order_template.xml",
    ],
}
