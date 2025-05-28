#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
import json
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from openupgradelib import openupgrade_merge_records

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config, float_round, ormcache


class AgreementColType(models.Model):
    _name = "edi.unilever.agreement.col.type"
    _description = "Edi unilever agreement col type"

    name = fields.Char()
    unilever_rappel_group_id = fields.Many2one(
        comodel_name="unilever.rappel.group",
        string="UL rappel group",
        ondelete="restrict",
    )
    unilever_ref = fields.Char(string="Unilever Ref.")


class UnileverAgreementCommunication(models.Model):
    _inherit = "edi.backend.mixin"
    _name = "unilever.agreement.communication"
    _description = "Unilever Agreement Communication"

    agreement_id = fields.Many2one(
        comodel_name="agreement",
        auto_join=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        auto_join=True,
    )
    move_type = fields.Selection(
        [("", "Sin informar"), ("A", "Alta"), ("B", "Baja"), ("M", "Modificación")],
        string="Move Type",
        default="A",
    )


class Agreement(models.Model):
    _inherit = ["agreement", "edi.backend.mixin"]
    _name = "agreement"

    name = fields.Char()
    active = fields.Boolean(string="Active", default=True)
    code = fields.Char()  # el 67
    # DTO file
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.user.company_id.id,
    )
    agreement_type = fields.Char(
        string="UL Agreement Type",
        related="agreement_type_id.code",
        index=True,
    )
    col_type_id = fields.Many2one(
        comodel_name="edi.unilever.agreement.col.type", string="COL type"
    )
    move_type = fields.Selection(
        [("", "Sin informar"), ("A", "Alta"), ("B", "Baja"), ("M", "Modificación")],
        string="Move Type",
        default="A",
    )
    partner_id = fields.Many2one(domain=[], index=True)
    grouped_group = fields.Boolean(
        string="Grouped group",
        compute="_compute_rappel_group",
        store=True,
        readonly=False,
    )
    grouped_subgroup = fields.Boolean(
        string="Grouped subgroup",
        compute="_compute_rappel_group",
        store=True,
        readonly=False,
    )
    product_group_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Group",
    )
    product_subgroup_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Subgroup",
    )
    # TODO: Remove field year
    year = fields.Integer(string="Year", default=lambda y: fields.Date.today().year)
    start_date = fields.Date(
        string="From Date",
        required=True,
        index=True,
    )
    end_date = fields.Date(string="To Date", index=True)
    unilever_participation_percent = fields.Float(
        string="% Unilever Participation",
    )
    estimated_consumption = fields.Float(string="Estimated Consumption")
    invoice_discount = fields.Float(
        string="% Invoice Discount",
    )
    anual_discount_percent = fields.Char(
        string="% Anual Discount",
        compute="_compute_anual_discount_percent",
        inverse="_inverse_anual_discount_percent",
        store=True,
    )
    # For DTO agreements
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
    )
    # For DTO agreements temporal fields to communicate to Unilever
    chain = fields.Boolean(string="Chain")

    # For POL and GIRA conditions
    product_ids = fields.Many2many(
        comodel_name="product.product",
        compute="_compute_product_ids",
        string="Products",
    )
    # COL file
    signature_date = fields.Date(
        default=fields.Date.context_today,
        string="Agreement Date",
    )
    signature_date_for_unilever = fields.Date(
        compute="_compute_signature_date_for_unilever",
        string="Agreement date for Unilever",
    )
    agreement_amount = fields.Float(
        string="Agreement Amount",
    )
    note = fields.Text("Notes")
    channel = fields.Selection(
        [("FRI", "helado UL"), ("GRR", "Granderroble"), ("CRE", "Crestas la Galeta")],
        string="Channel",
        default="FRI",
    )
    # TODO: To remove when merge rappels
    unilever_rappel_group = fields.Char(string="UL rappel group(Not use)")
    unilever_rappel_subgroup = fields.Char(string="UL rappel subgroup(Not use)")
    unilever_rappel_group_id = fields.Many2one(
        comodel_name="unilever.rappel.group",
        string="UL rappel group",
        ondelete="restrict",
    )
    # POL file
    agreement_price = fields.Float(
        string="Agreement Price",
        digits="Product Price",
    )
    guaranteed_price = fields.Float(
        string="Guaranteed Price",
        digits="Product Price",
    )
    agreement_quantity = fields.Float(string="Quantity")
    pol_estimated_consumption = fields.Float(
        string="POL Estimated Consumption",
    )
    pol_group_estimated_consumption = fields.Float(
        string="POL Group Estimated Consumption",
    )
    date_low = fields.Date(
        string="Date Low",
    )
    # Import helpers
    dto_type = fields.Selection(
        [
            ("G", "Grupo ventas (Categoría)"),
            ("P", "Producto"),
            ("R", "Rappels"),
            ("S", "Familia (Categoría)"),
            ("T", "Turismo"),
            ("GIRA", "GIRA"),
        ],
        string="Dto type",
    )
    agreement_condition_id = fields.Many2one(
        comodel_name="edi.unilever.agreement.condition",
        ondelete="restrict",
    )
    unilever_ref = fields.Char(
        related="partner_id.unilever_ref",
    )
    unilever_ref_sam = fields.Char(
        related="partner_id.unilever_ref_sam",
    )
    previous_agreement_id = fields.Many2one(
        comodel_name="agreement",
        string="Previous agreement",
        readonly=True,
        help="Source agreement when an agreement is renewed",
    )
    partner_communication_ids = fields.One2many(
        comodel_name="unilever.agreement.communication", inverse_name="agreement_id"
    )
    company_group_id = fields.Many2one(
        comodel_name="res.partner", related="partner_id.company_group_id", store=True
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="partner_id.commercial_partner_id",
        store=True,
    )

    _sql_constraints = [
        (
            "code_partner_company_unique",
            "unique(id, code, partner_id, company_id)",
            "This agreement code already exists for this partner!",
        )
    ]

    @api.depends("unilever_rappel_group_id")
    def _compute_rappel_group(self):
        for rec in self:
            rec.grouped_group = rec.unilever_rappel_group_id.grouped_group
            rec.grouped_subgroup = rec.unilever_rappel_group_id.grouped_subgroup

    # TT33897
    @api.constrains("rebate_section_ids")
    def _check_amount_to(self):
        sections = self.rebate_section_ids.sorted("amount_to")
        error = False
        previous_amount_from = 0.0
        previous_amount_to = 0.0
        for index, section in enumerate(sections):
            if (
                section.amount_from < previous_amount_from
                or section.amount_to < previous_amount_to
            ):
                error = True
                break
            if section.amount_from > section.amount_to:
                error = True
                break
            if index > 0 and section.amount_from <= previous_amount_to:
                error = True
                break
            previous_amount_from = section.amount_from
            previous_amount_to = section.amount_to
            if not config["test_enable"] and index == len(sections) - 1:
                if section.amount_to != 99999999.99:
                    error = True
        if error:
            raise ValidationError(
                _("Error In rebate section.\n" "Please, review the amount values")
            )
        return True

    @api.depends("agreement_condition_id")
    def _compute_product_ids(self):
        for agreement in self:
            if agreement.product_id:
                agreement.product_ids = agreement.product_id
            else:
                condition = agreement.agreement_condition_id
                agreement.product_ids = condition.mapped("line_ids.product_id")

    def _compute_signature_date_for_unilever(self):
        # Enviar la fecha del contrato como si fuese de este año.
        # Realmente se debería hacer una renovacion del acuerdo pero bueno...
        for rec in self:
            if not rec.signature_date:
                rec.signature_date_for_unilever = False
            date_send = rec.signature_date + relativedelta(
                years=fields.Date.today().year - rec.signature_date.year
            )
            rec.signature_date_for_unilever = date_send

    @api.onchange("agreement_condition_id")
    def onchange_agreement_condition_id(self):
        if self.agreement_condition_id.start_date:
            self.start_date = self.agreement_condition_id.start_date
        if self.agreement_condition_id.end_date:
            self.end_date = self.agreement_condition_id.end_date

    @api.onchange("col_type_id")
    def onchange_col_type_id(self):
        if not self.unilever_rappel_group_id:
            self.unilever_rappel_group_id = self.col_type_id.unilever_rappel_group_id

    @api.onchange(
        "partner_id",
        "invoice_discount",
        "anual_discount_percent",
        "unilever_rappel_group_id",
        "agreement_price",
        "agreement_condition_id",
    )
    def onchange_warning_renew(self):
        if (
            self._origin.create_date
            and self._origin.create_date
            < fields.Datetime.now() - relativedelta(months=1)
        ):
            warning_mess = {
                "title": _("Agreement created more than 1 month ago"),
                "message": _("You must be renew the contract instead of modify it"),
            }
            return {"warning": warning_mess}

    def write(self, vals):
        if self.env.context.get("skip_update_unilever_check"):
            return super().write(vals)
        active_vals = vals.get("active")
        if active_vals is False:
            today = fields.Date.today()
            vals.update(
                {
                    "date_low": today,
                    "end_date": today,
                    "move_type": "B",
                }
            )
        res = super().write(vals)
        communications = self.mapped("partner_communication_ids")
        if active_vals is False:
            communications.write(
                {
                    "move_type": "B",
                    "unilever_state": "not_sent",
                }
            )
        else:
            records_sent = communications.filtered(lambda x: x.unilever_state == "sent")
            records_sent.write(
                {
                    "move_type": "M",
                    "unilever_state": "not_sent",
                }
            )
            (communications - records_sent).write(
                {
                    "move_type": "A",
                    "unilever_state": "not_sent",
                }
            )
        return res

    @ormcache("partners", "agreement_year", "products")
    def get_consumption(self, partners, agreement_year, products):
        domain = [
            ("date_order", ">=", f"{agreement_year - 1}-01-01"),
            ("date_order", "<", f"{agreement_year}-01-01"),
            ("product_id", "in", products.ids),
            ("order_id.partner_id", "in", partners.ids),
        ]
        lines_group = self.env["sale.order.line"].read_group(
            domain,
            ["company_id", "order_partner_id", "untaxed_amount_invoiced"],
            ["company_id", "order_partner_id"],
            lazy=False,
        )
        amount_group_dict = {
            g["order_partner_id"][0]: g["untaxed_amount_invoiced"] for g in lines_group
        }
        return amount_group_dict

    def action_compute_estimated_consumption(self):
        AgreementCondition = self.env["edi.unilever.agreement.condition"]
        grupo_H = self.env["unilever.rappel.group"].search(
            [("unilever_ref", "=", "H")], limit=1
        )
        for agreement in self:
            agreement_year = agreement.signature_date.year
            if agreement_year == 2019:
                agreement_year = 2020
            partners = (
                agreement.partner_id.commercial_partner_id.child_ids
                + agreement.partner_id
            )
            if agreement.agreement_type == "COL":
                rappel_group = agreement.unilever_rappel_group_id.parent_id
            elif agreement.agreement_type == "DTO":
                rappel_group = agreement.unilever_rappel_group_id
            else:
                rappel_group = grupo_H
            if not rappel_group:
                continue
            products = self.env["product.product"].search(
                [("unilever_rappel_group_id", "child_of", rappel_group.id)]
            )
            if not products:
                continue
            amount_group_dict = self.get_consumption(partners, agreement_year, products)
            amount_group_pol_dict = {}
            if agreement.agreement_type == "POL":
                tourism_groups = self.env["edi.unilever.tourism.group"].search(
                    [("unilever_ref", "in", ["79", "86", "87", "82"])]
                )
                conditions = AgreementCondition.search(
                    [("tourism_group_id", "in", tourism_groups.ids)]
                )
                products = conditions.mapped("line_ids.product_id")
                amount_group_pol_dict = self.get_consumption(
                    partners, agreement_year, products
                )
            amt_group = 0.0
            amt_group_pol = 0.0
            for partner in partners:
                amt_group += amount_group_dict.get(partner.id, 0.0)
                amt_group_pol += amount_group_pol_dict.get(partner.id, 0.0)
            agreement.write(
                {
                    "estimated_consumption": float_round(
                        amt_group, precision_rounding=10
                    ),
                    "pol_estimated_consumption": float_round(
                        amt_group, precision_rounding=10
                    ),
                    "pol_group_estimated_consumption": float_round(
                        amt_group_pol, precision_rounding=10
                    ),
                }
            )

    def get_agreement_quantity_from_report(self, start_date, end_date):
        return self.with_context(
            start_date=start_date,
            end_date=end_date,
        ).get_agreement_quantity()

    def get_agreement_quantity(self):
        detail_dic = self.env.context.get("detail_dic", {})
        from_report = self.env.context.get("from_report", False)
        start_date = self.env.context.get("start_date")
        end_date = self.env.context.get("end_date")
        code = self.env.context.get("code")
        InvoiceLine = self.env["account.move.line"]
        quantity = 0.0
        for rec in self:
            start_date = max(filter(None, [start_date, rec.start_date]))
            end_date = min(filter(None, [end_date, rec.end_date]))
            domain = [
                ("move_id.invoice_date", ">=", start_date),
                ("move_id.invoice_date", "<=", end_date),
                (
                    "partner_id",
                    "in",
                    rec.partner_id.ids + rec.partner_id.company_group_member_ids.ids,
                ),
                ("product_id", "in", rec.product_ids.ids),
            ]
            if not from_report:
                domain.extend(
                    [
                        "|",
                        (
                            "unilever_communication_history_ids.edi_backend_id.code",
                            "!=",
                            code,
                        ),
                        ("unilever_communication_history_ids", "=", False),
                    ]
                )
            inv_lines = InvoiceLine.search(domain)
            if not inv_lines:
                continue
            quantity = 0.0
            for line in inv_lines:
                quantity += line.quantity * 1.00
            detail_dic[rec.id] = inv_lines.ids
        return quantity

    def _inverse_anual_discount_percent(self):
        for agreement in self:
            if (
                not agreement.anual_discount_percent
                or agreement.agreement_type != "DTO"
            ):
                agreement.rebate_section_ids = False
                continue
            sections = agreement.anual_discount_percent.split(";")
            section_list = []
            for section in sections:
                if not section:
                    continue
                section_value = section.split("-")
                amount_from = section_value[0]
                amount_to = section_value[1].split(":")[0]
                rebate_discount = section_value[1].split(":")[1]
                section_list.append(
                    {
                        "amount_from": round(float(amount_from.replace(",", ".")), 2),
                        "amount_to": round(float(amount_to.replace(",", ".")), 2),
                        "rebate_discount": round(
                            float(rebate_discount.replace(",", ".")), 2
                        ),
                    }
                )
            agreement.rebate_section_ids = [(5, 0)] + (
                [(0, 0, s) for s in section_list]
            )

    @api.depends("rebate_section_ids")
    def _compute_anual_discount_percent(self):
        for agreement in self:
            list_sections = []
            for section in agreement.rebate_section_ids:
                list_sections.append(
                    "{:.2f}-{:.2f}:{:.2f}".format(
                        section.amount_from, section.amount_to, section.rebate_discount
                    )
                )
            agreement.anual_discount_percent = ";".join(list_sections)

    @api.model
    def create(self, vals):
        if (
            not vals.get("rebate_type", False)
            and vals.get("agreement_type_id", False)
            == self.env.ref("edi_backend_ulv.DTO").id
        ):
            vals["rebate_type"] = "section_total"
        agreement = super().create(vals)
        if vals.get("agreement_type_id", False) in (
            self.env.ref("edi_backend_ulv.DTO").id,
            self.env.ref("edi_backend_ulv.COL").id,
            self.env.ref("edi_backend_ulv.POL").id,
        ):
            agreement.create_partner_state()
        return agreement

    def get_similar_agreements(self, partner_ids=False):
        agreements = self.env["agreement"].search(
            [
                ("id", "!=", self.id),
                ("partner_id", "in", partner_ids or self.partner_id.ids),
                ("agreement_type_id", "=", self.agreement_type_id.id),
                (
                    "unilever_rappel_group_id",
                    "=",
                    self.unilever_rappel_group_id.id,
                ),
                (
                    "agreement_condition_id",
                    "=",
                    self.agreement_condition_id.id,
                ),
                "|",
                ("end_date", ">", self.start_date),
                ("end_date", "=", False),
                # Conditions to merge agreements
                # (
                #     "anual_discount_percent",
                #     "=",
                #     self.anual_discount_percent,
                # ),
                # ("start_date", "=", self.start_date),
                # ("end_date", "=", self.end_date),
            ]
        )
        return agreements

    def get_similar_agreement_communication(self, partner_id=False):
        agreement_communication = self.env["unilever.agreement.communication"].search(
            [
                ("agreement_id", "!=", self.id),
                ("agreement_id.partner_id", "=", partner_id or self.partner_id.id),
                ("agreement_id.agreement_type_id", "=", self.agreement_type_id.id),
                (
                    "agreement_id.unilever_rappel_group_id",
                    "=",
                    self.unilever_rappel_group_id.id,
                ),
                (
                    "agreement_id.agreement_condition_id",
                    "=",
                    self.agreement_condition_id.id,
                ),
                "|",
                ("agreement_id.end_date", ">", self.start_date),
                ("agreement_id.end_date", "=", False),
            ]
        )
        return agreement_communication

    def create_partner_state(self):
        vals_list = []
        for agreement in self:
            for partner in agreement.partner_id.unilever_child_partner_ids:
                vals_list.append(
                    {
                        "agreement_id": agreement.id,
                        "partner_id": partner.id,
                        "unilever_state": "not_sent",
                    }
                )
        return self.env["unilever.agreement.communication"].create(vals_list)

    def update_partner_state(self):
        vals_list = []
        for agreement in self:
            for partner in agreement.partner_id.unilever_child_partner_ids:
                vals_list.append(
                    {
                        "agreement_id": agreement.id,
                        "partner_id": partner.id,
                        "unilever_state": "not_sent",
                    }
                )
        return self.env["unilever.agreement.communication"].create(vals_list)

    def merge_agreements(self):
        AGREEMENT_MERGE_OPS = {f: "no merge" for f in self._fields}
        agreement_dic = defaultdict(lambda: self.browse())
        for agreement in self:
            company_group = agreement.partner_id.company_group_id
            comercial_partner = agreement.partner_id.commercial_partner_id
            if company_group:
                partner_key = company_group
            else:
                partner_key = comercial_partner
            key = (
                partner_key.id,
                agreement.agreement_type_id.id,
                agreement.unilever_rappel_group_id.id,
                agreement.product_id.id,
                agreement.product_group_id.id,
                agreement.product_subgroup_id.id,
                agreement.invoice_discount,
                agreement.agreement_condition_id.id,
                agreement.anual_discount_percent,
                agreement.start_date,
                agreement.end_date,
                agreement.date_low,
                agreement.active,
            )
            agreement_dic[key] |= agreement

        for key, agreements in agreement_dic.items():
            target_agreement = agreements.filtered(
                lambda ag, k=key: ag.partner_id.id == k[0]
            )[:1]
            source_agreements = agreements - target_agreement
            if not source_agreements.exists() or not target_agreement.exists():
                continue
            openupgrade_merge_records.merge_records(
                self.env,
                "agreement",
                source_agreements.ids,
                target_agreement.id,
                AGREEMENT_MERGE_OPS,
                method="sql",
            )

    def action_set_anual_percent_discount_default(self):
        if not self.agreement_type == "DTO":
            return ValidationError(_("This agreement is not DTO type"))
        self.anual_discount_percent = self.company_id.anual_percent_discount_default

    def action_ulv_communication_history(self):
        """Try to open the communication history where any of partner communication
        records was send to Unilever
        """
        self.ensure_one()
        CommunicationHistory = self.env["edi.backend.communication.history"]
        history_backend = CommunicationHistory.browse()
        history_backends = CommunicationHistory.search(
            [
                ("create_date", ">=", self.create_date),
                ("edi_backend_id.code", "=", self.agreement_type),
            ]
        )
        if self.agreement_type == "DTO":
            for history in history_backends:
                history_move_set = set(json.loads(history.applied_records))
                partner_communication_set = set(self.partner_communication_ids.ids)
                if history_move_set & partner_communication_set:
                    history_backend = history
                    break
        else:
            for history in history_backends:
                history_move_set = set(json.loads(history.applied_records))
                agreement_set = set(self.ids)
                if history_move_set & agreement_set:
                    history_backend = history
                    break
        if history_backend:
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "base_edi_backend.action_edi_backend_communication_history"
            )
            action["domain"] = [("id", "in", history_backend.ids)]
            return action
        else:
            raise UserError(
                _("There is no file sent to Unilever containing this agreement")
            )
