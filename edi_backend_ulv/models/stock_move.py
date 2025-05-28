#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class StockMove(models.Model):
    _inherit = ["stock.move", "edi.backend.mixin"]
    _name = "stock.move"

    amount_tourism_discount = fields.Float(
        compute="_compute_amount_discount",
        string="Amount Tourism Discount",
    )
    amount_unilever_participation = fields.Float(
        compute="_compute_amount_discount",
        string="Amount Unilever Participation",
    )
    amount_dealer_participation = fields.Float(
        compute="_compute_amount_discount",
        string="Amount Dealer Participation",
    )
    unilever_agreement_id = fields.Many2one(
        comodel_name="agreement",
        compute="_compute_unilever_agreement_id",
    )
    unilever_quantity_done = fields.Float(
        string="Unilever Qty done",
        compute="_compute_unilever_quantity_done",
        digits="Product Unit of Measure",
    )
    unilever_list_price = fields.Float(
        string="Unilever Sales Price",
        digits="Product Price",
        compute="_compute_unilever_list_price",
    )
    is_return = fields.Boolean(compute="_compute_is_return")

    def _compute_unilever_agreement_id(self):
        for line in self:
            line.unilever_agreement_id = line.sale_line_id.unilever_agreement_id

    def _compute_amount_discount(self):
        for line in self:
            agreement = line.unilever_agreement_id
            line.amount_tourism_discount = 0.0
            if agreement.agreement_type == "POL":
                line.amount_tourism_discount = line.quantity_done * (
                    agreement.guaranteed_price - agreement.agreement_price
                )
            else:
                amount_dto = (
                    line.unilever_list_price * line.quantity_done
                    - line.sale_line_id.price_subtotal
                )
                unilever_participation = amount_dto * (
                    agreement.unilever_participation_percent / 100
                )
                if unilever_participation == 0 and amount_dto:
                    # Force 80% Unilever 20% Dealer
                    # https://www.tecnativa.com/web#id=18330&view_type=form&
                    # model=project.task
                    unilever_participation = amount_dto * (80 / 100)
                line.amount_unilever_participation = unilever_participation
                line.amount_dealer_participation = amount_dto - unilever_participation

    def _compute_unilever_quantity_done(self):
        # Calcular unidades en cajas segun indicaciones del cliente.
        # https://www.tecnativa.com/web#id=18462&view_type=form&
        # model=project.task
        # Si(UDM del albarán = Unidad):
        #     Si(producto tiene 2a UDM = Caja)
        #         cantidad_cajas = cantidad / factor de conversion
        #         Si(es_entero(cantidad_cajas)):
        #             Enviar cantidad_cajas
        # Enviar cantidad_albarán (en cualquier otro caso)
        uom_unit = self.env.ref("uom.product_uom_unit")
        for line in self:
            line.unilever_quantity_done = line.quantity_done
            # Allways send secondary qty for knorr products. TT42543
            if (
                line.product_id.product_brand_id.unilever_ref == "FS_"
                and line.secondary_uom_qty
            ):
                line.unilever_quantity_done = line.secondary_uom_qty
                continue
            if line.product_uom == uom_unit:
                box = fields.first(
                    line.product_id.secondary_uom_ids.filtered(
                        lambda x: x.name.upper() == "CAJA"
                    )
                )
                factor = box.factor or 1.0
                if line.quantity_done % factor == 0.0:
                    line.unilever_quantity_done = line.quantity_done / factor

    def _compute_unilever_list_price(self):
        """
        Compute list_price for Unilever products from unilever pricelist
        instead of product price_list field
        """
        pricelist = self.env.ref("edi_backend_ulv.edi_unilever_pricelist")
        for line in self:
            line.unilever_list_price = pricelist.get_product_price(
                line.product_id.product_tmpl_id,
                line.quantity_done,
                False,
                date=line.date,
            )

    def _compute_is_return(self):
        for move in self:
            move.is_return = True if move.origin_returned_move_id else False
