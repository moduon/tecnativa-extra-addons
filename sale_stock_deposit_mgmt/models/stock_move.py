# Copyright 2023 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):

    _inherit = "stock.move"

    def _key_assign_picking(self):
        """
        En un ambito de multi steps y una regla push, odoo no tiene en cuenta el partner
        a la hora de asignar un picking para el nuevo move resultante de aplicar
        la regla push
        """
        keys = super(StockMove, self)._key_assign_picking()
        if self.partner_id != keys[-1] and self.picking_type_id.code == "outgoing":
            keys += (self.partner_id,)
        return keys

    def _search_picking_for_assignation_domain(self):
        """
        En un ambito de multi steps y una regla push...
        """
        domain = super()._search_picking_for_assignation_domain()
        if self.picking_type_id.code == "outgoing":
            domain += [("partner_id", "=", self.partner_id.id)]
        return domain
