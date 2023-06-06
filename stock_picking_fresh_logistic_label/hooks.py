# Copyright 2022 Sergio Teruel - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """
    Update product label coefficient for all products which have a KG uom unit
    as primary unit
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    uom_kg = env.ref("uom.product_uom_kgm")
    products = (
        env["product.template"]
        .with_context(active_test=False)
        .search([("uom_id", "=", uom_kg.id)])
    )
    for product in products:
        product.label_coefficient = 6
