#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = ["res.partner", "edi.backend.mixin"]
    _name = "res.partner"

    unilever_move_type = fields.Selection(
        [("A", "New partner"), ("M", "Updated partner"), ("B", "Disabled partner")],
        string="Unilever move type",
        copy=False,
    )
    unilever_partner_type = fields.Selection(
        [("C", "Direct Partner"), ("F", "SAM Indirect Partner")],
        string="Unilever Partner Type",
    )
    unilever_ref = fields.Char(
        string="Unilever Ref",
        size=7,
        copy=False,
    )
    unilever_ref_sam = fields.Char(
        string="Unilever Ref SAM",
        size=10,
        copy=False,
    )
    unilever_category_id = fields.Many2one(
        comodel_name="edi.unilever.category",
        string="Unilever category",
    )
    unilever_competency_id = fields.Many2one(
        comodel_name="edi.unilever.competency",
        string="Unilever competency",
    )
    unilever_high_competency_id = fields.Many2one(
        comodel_name="edi.unilever.competency",
        string="Unilever high competency",
    )
    unilever_disable_reason_id = fields.Many2one(
        comodel_name="edi.unilever.disable.reason",
        string="Unilever disable reason",
        copy=False,
    )
    unilever_local_code = fields.Integer(
        string="Unilever local code",
    )
    unilever_center = fields.Char(
        string="Unilever center",
        size=2,
    )
    self_employed = fields.Boolean(
        compute="_compute_self_employed",
        string="Self employed",
    )
    unilever_commercial_name = fields.Char(
        compute="_compute_unilever_commercial_name",
        string="Unilever commercial name",
    )
    unilever_seasonality = fields.Selection(
        [
            ("yearly", "Yearly"),
            ("season", "Season"),
        ],
        string="Seasonality",
        default="yearly",
    )
    unilever_agreement_communication_ids = fields.One2many(
        comodel_name="unilever.agreement.communication", inverse_name="partner_id"
    )
    unilever_child_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_unilever_child_partner_ids",
    )

    def get_contact_by_position(self, position):
        if self.self_employed:
            return self.browse()
        contacts = self.child_ids.filtered(lambda x: x.type == "contact")
        if position > len(contacts):
            return self.browse()
        return contacts[position - 1]

    @api.model
    def get_agreement_communication_fields(self):
        return ["unilever_ref", "parent_id", "company_group_id", "active"]

    @api.model
    def create(self, vals):
        if not self.env.context.get("skip_update_unilever_check"):
            if "create_date" in vals:
                if vals.get("unilever_ref", False) or vals.get(
                    "unilever_ref_sam", False
                ):
                    vals["unilever_move_type"] = "A"
        res = super().create(vals)
        if any(f_name in vals for f_name in self.get_agreement_communication_fields()):
            res.update_agreement_communication()
        return res

    def write(self, vals):
        if self.env.context.get("skip_update_unilever_check"):
            return super().write(vals)
        # HACK to resolve https://github.com/odoo/odoo/blob/
        # 2940ee6b356fd167f5ece62c92f9a9e8a770aa7d/odoo/addons/base/res/
        # res_partner.py#L519
        if "is_company" in vals:
            super().write({"is_company": vals.pop("is_company")})
        if "unilever_state" not in vals:
            vals["unilever_state"] = "not_sent"
        active_vals = vals.get("active")
        if active_vals is True:
            vals["unilever_move_type"] = "M"
            super().write(vals)
        elif active_vals is False:
            vals["unilever_move_type"] = "B"
            super().write(vals)
        else:
            archived_partners = self.filtered(lambda x: not x.active)
            super(ResPartner, archived_partners).write(vals)
            active_partners = self - archived_partners
            partners_sent = active_partners.filtered(
                lambda x: x.unilever_state == "sent"
            )
            vals["unilever_move_type"] = "M"
            super(ResPartner, partners_sent).write(vals)
            vals["unilever_move_type"] = "A"
            super(ResPartner, active_partners - partners_sent).write(vals)
        if any(f_name in vals for f_name in self.get_agreement_communication_fields()):
            self.update_agreement_communication()
        return True

    @api.constrains("unilever_ref", "unilever_ref_sam", "unilever_local_code")
    def _constrains_unilever_ref_sam(self):
        for partner in self:
            if len(partner.unilever_ref or "") > 7:
                raise UserError(_("Unilever reference length > 7"))
            if len(partner.unilever_ref_sam or "") > 10:
                raise UserError(_("Unilever references SAM length > 10"))
            if partner.unilever_local_code > 9999999:
                raise UserError(_("Unilever local code can't have more than 7 digits"))

    def _compute_self_employed(self):
        for partner in self:
            partner_vat = partner.vat or partner.commercial_partner_id.vat
            if not partner_vat:
                partner.self_employed = False
                continue
            clean_vat = partner_vat.replace(" ", "").replace("-", "")
            vat = clean_vat if len(clean_vat) <= 9 else partner_vat[2:]
            if not re.match("^[A-Z]", vat):
                partner.self_employed = True
            else:
                partner.self_employed = False

    def _compute_unilever_commercial_name(self):
        for partner in self:
            name = False
            if partner.parent_id:
                name = partner.comercial or partner.name
            if not name:
                name = partner.commercial_partner_id.comercial
            if not name:
                # TT36126
                if partner.self_employed:
                    # Case 1. Try to retrieve first child delivery contact
                    first_child = partner.child_ids.filtered(
                        lambda p: p.type == "delivery"
                    )[:1]
                    if first_child:
                        name = first_child.name
                    # Case 2. Try get spanish comercial field
                    if not name:
                        name = partner.comercial
                    # Case 3. get partner name
                    if not name:
                        name = partner.name
                else:
                    name = partner.commercial_partner_id.name
            partner.unilever_commercial_name = name

    def _compute_unilever_child_partner_ids(self):
        for partner in self:
            child_of_chain = self.search([("company_group_id", "=", partner.id)])
            partner.unilever_child_partner_ids = (
                partner
                | partner.child_ids.filtered(lambda p: p.type == "delivery")
                | child_of_chain
            )

    def get_ancestor_and_company_group_partners(self):
        """Get all partners in the hierarchy of the current partner"""
        self.ensure_one()
        all_partners = self
        parent_partner = self.parent_id
        while parent_partner:
            all_partners |= parent_partner
            parent_partner = parent_partner.parent_id
        all_partners |= self.company_group_id
        return all_partners

    def update_agreement_communication(self):
        """Create agreement comunications for each partner in all affected agreements"""
        vals_list = []
        rel_partners_dic = {}
        all_partners = self.browse()
        unilever_partners = self.filtered("unilever_ref")
        # Fill dictionary with all partners and their ancestors
        for partner in unilever_partners:
            rel_partners_dic[
                partner
            ] = partner.get_ancestor_and_company_group_partners()
            all_partners += rel_partners_dic[partner]
        today = fields.Date.context_today(self)
        agreements = self.env["agreement"].search(
            [
                "&",
                "&",
                "&",
                ("agreement_type", "!=", False),
                ("partner_id", "in", all_partners.ids),
                "|",
                ("date_low", "=", False),
                ("date_low", ">=", today),
                "|",
                ("end_date", "=", False),
                ("end_date", ">=", today),
            ]
        )
        communications = self.env["unilever.agreement.communication"].search(
            [
                ("partner_id", "in", unilever_partners.ids),
            ]
        )
        for partner in unilever_partners.filtered("active"):
            processed_agreements = agreements.browse()
            for rel_partner in rel_partners_dic[partner]:
                partner_agreements = agreements.filtered(
                    lambda x, rp=rel_partner: x.partner_id == rp
                )
                for agreement in partner_agreements - processed_agreements:
                    processed_agreements |= agreement
                    pa_communication = communications.filtered(
                        lambda x, a=agreement, p=partner: x.agreement_id == a
                        and x.partner_id == p
                    )
                    if pa_communication:
                        communications -= pa_communication
                        # Establecer comuniaciones dadas de baja como modificadas
                        to_modify = pa_communication.filtered(
                            lambda pac: pac.move_type == "B"
                        )
                        to_modify.write(
                            {
                                "unilever_state": "not_sent",
                                "move_type": "M",
                            }
                        )
                    else:
                        vals_list.append(
                            {
                                "agreement_id": agreement.id,
                                "partner_id": partner.id,
                                "unilever_state": "not_sent",
                            }
                        )
        # Eliminar comuniaciones de alta no procesadas que no habían sido enviadas
        to_unlink = communications.filtered(
            lambda c: c.move_type == "A" and c.unilever_state == "not_sent"
        )
        communications -= to_unlink
        to_unlink.unlink()
        # Dar de baja comunicaciones no procesadas enviadas previamente
        communications.filtered(lambda c: c.move_type != "B").write(
            {"move_type": "B", "unilever_state": "not_sent"}
        )
        return self.env["unilever.agreement.communication"].create(vals_list)

    def send_unilever_cli(self):
        """
        Process to generate CLI Unilever file directly from selected partners
        """
        unilever_cli = self.env["edi.backend"].search([("code", "=", "CLI")], limit=1)
        if not unilever_cli:
            raise ValidationError(_("There is not backend (CLI) to process data!"))
        partners_error = self.filtered(lambda p: not p.unilever_ref)
        if partners_error:
            raise UserError(
                _(
                    "There are partners without Unilever reference %s"
                    % "\n".join(partners_error.mapped("name"))
                )
            )
        history = self.env["edi.backend.communication.history"].create(
            {
                "edi_backend_id": unilever_cli.id,
                "state": "sent",
                "applied_domain": [("id", "in", self.ids)],
            }
        )
        history.action_rebuild_file()
        return history.get_formview_action()

    def action_agreement_unilever_rebate(self):
        self.ensure_one()
        agreements = self.env["agreement"].search(
            [("partner_id", "=", self.id), ("is_rebate", "=", True)]
        )

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "agreement.agreement_action"
        )
        action["domain"] = [("id", "in", agreements.ids)]
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_agreement_type_id": self.env.ref("edi_backend_ulv.DTO").id,
                "default_partner_id": self.id,
            }
        )
        action["context"] = ctx
        return action

    def action_agreement_unilever_GIRA(self):
        self.ensure_one()
        agreements = self.env["agreement"].search(
            [("partner_id", "=", self.id), ("agreement_type_id.code", "=", "GIRA")]
        )
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "agreement.agreement_action"
        )
        action["domain"] = [("id", "in", agreements.ids)]
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_agreement_type_id": self.env.ref("edi_backend_ulv.GIRA").id,
                "default_partner_id": self.id,
            }
        )
        action["context"] = ctx
        return action
