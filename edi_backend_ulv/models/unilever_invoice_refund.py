#  Copyright 2022 Tecnativa - Carlos Roca
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class UnileverInvoiceRefund(models.Model):
    _name = "unilever.invoice.refund"
    _description = "Facturas de abono unilever"

    name = fields.Char(required=True)
    state = fields.Selection(
        selection=[("pending", "Pending"), ("confirm", "Confirm")], default="pending"
    )
    line_ids = fields.One2many(
        comodel_name="unilever.invoice.refund.line",
        inverse_name="invoice_id",
    )

    def action_confirm_payment_invoice(self):
        self.state = "confirm"


class UnileverInvoiceRefundLine(models.Model):
    _name = "unilever.invoice.refund.line"
    _description = "Lineas de factura de abono unilever"

    invoice_id = fields.Many2one(comodel_name="unilever.invoice.refund")
    line_type = fields.Selection(selection=[("D", "D")], required="True")
    week = fields.Integer()
    year = fields.Integer()
    product_id = fields.Many2one(comodel_name="product.product")
    quantity = fields.Float(digits="Product Unit of Measure")
    price = fields.Float(digits="Product Price")
    tpr = fields.Float(digits="Product Price")
    dto_conces = fields.Float(digits="Product Price")
    dto_early_pay = fields.Float(digits="Product Price")
    dto_volume = fields.Float(digits="Product Price")
    amount_to_invoice = fields.Float(digits="Product Price")
    amount_line = fields.Float(digits="Product Price")
    amount_distribution = fields.Float(digits="Product Price")
    picking_id = fields.Many2one(comodel_name="stock.picking")
    invoice_number = fields.Char()
