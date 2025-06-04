#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move"

    def _update_reserved_quantity(
        self,
        need,
        available_quantity,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=True,
    ):
        lot_id = self.env.context.get("force_lot_fresh_asset", lot_id)
        return super()._update_reserved_quantity(
            need,
            available_quantity,
            location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
        )

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        lot = self.env.context.get("force_lot_fresh_asset", False)
        if lot:
            if self.move_orig_ids:
                lot_orig = self.move_orig_ids.move_line_ids.filtered(
                    lambda ml: ml.lot_id == lot
                ).lot_id
                vals["lot_id"] = lot_orig and lot_orig.id or False
                vals["lot_name"] = lot_orig and lot_orig.name or False
            vals.update(
                {
                    "lot_id": vals.get("lot_id", lot.id),
                    "lot_name": vals.get("lot_name", lot.name),
                }
            )
        return vals
