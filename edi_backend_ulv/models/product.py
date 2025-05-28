#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    unilever_ref = fields.Char(string="Unilever Ref")
    # TODO: To remove when merge rappels
    unilever_rappel_group = fields.Char(string="UL rappel group(Not use)")
    unilever_rappel_subgroup = fields.Char(string="UL rappel subgroup(Not use)")
    unilever_rappel_group_id = fields.Many2one(
        comodel_name="unilever.rappel.group",
        string="UL rappel group",
        ondelete="restrict",
    )


class ProductCategory(models.Model):
    _inherit = "product.category"

    unilever_ref = fields.Char(string="Unilever Ref")
