# Copyright 2021 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductSetAdd(models.TransientModel):
    _inherit = "product.set.add"

    def add_set(self):
        sale_order = self.env["sale.order"].search(
            [
                ("partner_shipping_id", "=", self.order_id.partner_shipping_id.id),
                ("ul_set_id.id", "!=", None),
                ("date_order", ">=", "%s-1-1" % fields.Date.today().year),
                ("date_order", "<=", "%s-12-31" % fields.Date.today().year),
                ("state", "!=", "cancel"),
            ]
        )
        if self.product_set_id.is_ul_fill and not sale_order:
            self.order_id.write({"ul_set_id": self.product_set_id.id})
        elif self.product_set_id.is_ul_fill and sale_order:
            raise UserError(
                _(
                    "In order %s the filling operation has "
                    "already been carried out for the delivery address selected "
                    "this year."
                )
                % sale_order.name
            )
        res = super().add_set()
        for line in self.order_id.order_line:
            if not line.discount:
                # Need to save the actual price unit to avoid recompute it
                unit_price = line.price_unit
                # Recompute the discount for the line from pricelist
                # TODO: ¿Que se quiere hacer? ¿Descuento de la tarifa?
                # ¿Descuento del acuerdo?
                line.product_uom_change()
                agreement_discount = line.get_agreement_values().get("discount", 0.0)
                if agreement_discount:
                    line.discount = agreement_discount
                # Recover the old price unit
                line.price_unit = unit_price
        return res

    def prepare_sale_order_line_data(self, set_line, max_sequence=0):
        res = super(
            ProductSetAdd, self.with_context(skip_unilever_reset_discount=True)
        ).prepare_sale_order_line_data(set_line, max_sequence)
        res["price_unit"] = set_line.price_unit
        return res
