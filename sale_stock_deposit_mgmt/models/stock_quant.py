# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, models
from odoo.exceptions import UserError
from odoo.tests import Form


class StockQuant(models.Model):

    _inherit = "stock.quant"

    def action_create_deposit_picking(self):
        ctx = dict(self.env.context, deposit_picking_mgmt=True)
        view = "sale_stock_deposit_mgmt.view_picking_deposit_form"
        with Form(self.env["stock.picking"].with_context(**ctx), view) as picking_form:
            owner_id = self[:1].owner_id
            picking_form.partner_id = owner_id
            for quant in self:
                if (
                    not quant.owner_id
                    or quant.owner_id.commercial_partner_id
                    != owner_id.commercial_partner_id
                ):
                    raise UserError(_("Incorrect owners"))
                available_qty = quant.quantity - quant.reserved_quantity
                if available_qty <= 0.0:
                    continue
                with picking_form.move_ids_without_package.new() as line_form:
                    line_form.product_id = quant.product_id
                    line_form.product_uom_qty = available_qty
        action = self.env.ref("sale_stock_deposit_mgmt.action_deposit_picking").read()[
            0
        ]
        action["views"] = [(self.env.ref(view).id, "form")]
        action["res_id"] = picking_form.id
        return action
