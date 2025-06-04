#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = "product.category"

    is_unilever_mef = fields.Boolean(string="Unilever MEF")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_unilever_mef = fields.Boolean(
        string="Unilever MEF",
        related="categ_id.is_unilever_mef",
    )

    def get_unilever_agreement_mef(self):
        agreements = self.env["agreement"].search(
            [
                ("mef_product_id", "in", self.product_variant_ids.ids),
                ("domain", "=", "unilever_mef"),
            ]
        )
        return agreements

    def get_unilever_agreement_mef_action(self, agreements):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "agreement.agreement_action"
        )
        action["domain"] = [("id", "in", agreements.ids)]
        return action

    def action_agreement_unilever_mef(self):
        self.ensure_one()
        agreements = self.get_unilever_agreement_mef()
        if not agreements:
            raise UserError(_("Agreements not found!"))
        action_dict = self.get_unilever_agreement_mef_action(agreements)
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_agreement_type_id": self.env.ref(
                    "agreement_unilever_mef.agreement_type_mef"
                ).id,
                "default_product_id": self.product_variant_id.id,
            }
        )
        action_dict["context"] = ctx
        return action_dict


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_agreement_unilever_mef(self):
        self.ensure_one()
        agreements = self.product_tmpl_id.get_unilever_agreement_mef()
        if not agreements:
            raise UserError(_("Agreements not found!"))
        action_dict = self.product_tmpl_id.get_unilever_agreement_mef_action(agreements)
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_agreement_type_id": self.env.ref(
                    "agreement_unilever_mef.agreement_type_mef"
                ).id,
                "default_product_id": self.id,
            }
        )
        action_dict["context"] = ctx
        return action_dict
