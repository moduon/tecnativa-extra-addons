# Copyright 2022 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock Picking Fresh Logistic Label",
    "version": "16.0.1.0.0",
    "author": "Tecnativa",
    "website": "https://github.com/Tecnativa/extra-addons",
    "category": "Stock Inventory",
    "license": "AGPL-3",
    "depends": [
        "company_sanitary_registry",
        "stock_picking_batch_extended",
        "l10n_es_partner",
        "product_fishing",
        "product_fao_fishing",
    ],
    "data": [
        "reports/report_picking_logistic_label.xml",
        "data/report_paperformat.xml",
        "reports/report_actions.xml",
        "views/product_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "post_init_hook": "post_init_hook",
}
