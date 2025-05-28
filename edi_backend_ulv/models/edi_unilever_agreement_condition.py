#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
from odoo import api, fields, models


class EdiUnileverAgreementCondition(models.Model):
    _name = "edi.unilever.agreement.condition"
    _description = "Edi unilever agreement condition"

    name = fields.Char()
    code = fields.Char()
    start_date = fields.Date(string="From Date")
    end_date = fields.Date(string="To Date")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.user.company_id.id,
    )
    condition_type = fields.Selection(
        [("GIRA", "Descuento GIRA"), ("POL", "Política de turismo y liquidaciones")],
        string="Condition Type",
    )
    line_ids = fields.One2many(
        comodel_name="edi.unilever.agreement.condition.line",
        inverse_name="agreement_condition_id",
        copy=True,
    )
    tourism_group_id = fields.Many2one(
        string="Tourism group",
        comodel_name="edi.unilever.tourism.group",
        ondelete="restrict",
    )


class EdiUnileverAgreementConditionLine(models.Model):
    _name = "edi.unilever.agreement.condition.line"
    _description = "Edi unilever agreement condition line"

    agreement_condition_id = fields.Many2one(
        comodel_name="edi.unilever.agreement.condition",
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
        string="Product",
    )
    condition_price = fields.Float(
        string="Price",
        digits="Product Price",
    )
    condition_discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
    )


class EdiUnileverTourismGroup(models.Model):
    _name = "edi.unilever.tourism.group"
    _description = "Edi unilever tourism groups"

    name = fields.Char(
        string="Name",
        required=True,
    )
    unilever_ref = fields.Char(string="Unilever ref")
    minimal_price = fields.Float(string="Minimal price", digits="Product Price")
    guaranteed_price = fields.Float(string="Guaranteed price", digits="Product Price")

    @api.depends("name", "unilever_ref")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "[{}] {}".format(rec.unilever_ref or "", rec.name)
