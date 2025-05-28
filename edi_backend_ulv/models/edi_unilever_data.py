#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
from odoo import fields, models


class EdiUnileverData(models.AbstractModel):
    _name = "edi.unilever.data.mixin"
    _description = "Edi unilever data mixin"

    code = fields.Char(
        string="Code",
        required=True,
    )
    name = fields.Char(
        string="Name",
        required=True,
    )


class EdiUnileverCategory(models.Model):
    _inherit = "edi.unilever.data.mixin"
    _name = "edi.unilever.category"
    _description = "Unilever Category"

    code = fields.Integer(
        string="Code",
        required=True,
    )


class EdiUnileverCompetency(models.Model):
    _inherit = "edi.unilever.data.mixin"
    _name = "edi.unilever.competency"
    _description = "Unilever competency"


class EdiUnileverDisableReason(models.Model):
    _inherit = "edi.unilever.data.mixin"
    _name = "edi.unilever.disable.reason"
    _description = "Unilever disable reason"
