# Copyright 2018 Sergio Teruel <sergio.teruel@tecnativa.com>
# Copyright 2018 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class DataIntegrityWiz(models.TransientModel):
    _name = "data.integrity.wiz"
    _description = "Data integrity check wizard"
    _rec_name = "check_type"

    check_type = fields.Selection(
        [
            ("unilever_dealer_chain", "Comprobar cadena Unilever en partners"),
            (
                "unilever_agreement_dto_chain",
                "Comprobar acuerdos Unilever tipo DTO por año y grupo para "
                "todos los partners con cadena asignada",
            ),
            ("unilever_agreement_chain_sync", "Comprobar check cadena en acuerdos"),
        ],
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="data.integrity.line.wiz",
        inverse_name="wizard_id",
        string="Lines",
        readonly=True,
    )

    def process_unilever_dealer_chain(self):
        self.line_ids = False
        ResPartner = self.env["res.partner"]
        ulv_partners = ResPartner.search(
            [
                ("unilever_ref", "!=", False),
            ]
        )
        ulv_commercial_partners = ulv_partners.mapped("commercial_partner_id")
        line_vals = []
        for commercial_partner in ulv_commercial_partners:
            all_partners = ResPartner.search(
                [
                    ("id", "child_of", commercial_partner.ids),
                ],
                order="unilever_dealer_chain DESC",
            )
            first_partner = all_partners[:1]
            first_chain = first_partner.unilever_dealer_chain
            alert_partners = all_partners.filtered(
                lambda p, fc=first_chain: p.unilever_dealer_chain != fc
                and not p.unilever_dealer_chain
            )
            if alert_partners:
                vals = {
                    "name": f"Registros con cadena vacía: {commercial_partner.name}",
                    "description": f"Partner con cadena: {first_partner.name} "
                    f"cadena: {first_chain} -> Registros sin cadena:",
                    "model_name": "res.partner",
                    "domain": "[]",
                    "affected_records": (first_partner | alert_partners).ids,
                }
                for p in alert_partners:
                    vals["description"] += f"\n{p.name}"
                line_vals.append((0, 0, vals))
            alert_partners = all_partners.filtered(
                lambda p, fp=first_partner: p.unilever_dealer_chain
                != fp.unilever_dealer_chain
                and p.unilever_dealer_chain
            )
            if alert_partners:
                vals = {
                    "name": f"Registros con cadena distinta: {commercial_partner.name}",
                    "description": f"Primer partner con cadena: {first_partner.name} "
                    f"cadena: {first_chain} -> Registros cadena distinta:",
                    "model_name": "res.partner",
                    "domain": "[]",
                    "affected_records": (first_partner | alert_partners).ids,
                }
                for p in alert_partners:
                    vals["description"] += f"\n{p.name}: {p.unilever_dealer_chain}"
                line_vals.append((0, 0, vals))
        self.line_ids = line_vals

    def process_unilever_agreement_dto_chain(self):
        self.line_ids = False
        ResPartner = self.env["res.partner"]
        ulv_partners = ResPartner.search(
            [
                ("unilever_dealer_chain", "!=", False),
            ]
        )
        ulv_chain_partners = ulv_partners.filtered(
            lambda p: p.unilever_ref and p.unilever_ref == str(p.unilever_dealer_chain)
        )
        line_vals = []
        for chain_partner in ulv_chain_partners:
            all_partners = ResPartner.search(
                [
                    ("unilever_dealer_chain", "=", chain_partner.unilever_dealer_chain),
                ],
            )
            agreements = self.env["agreement"].search(
                [
                    ("agreement_type", "=", "DTO"),
                    ("partner_id", "in", all_partners.ids),
                ]
            )
            for partner in all_partners - chain_partner:
                affected_records = agreements.browse()
                description = ""
                chain_agreements = agreements.filtered(
                    lambda a, cp=chain_partner: a.partner_id == cp
                )
                for chain_agreement in chain_agreements:
                    agreement = agreements.filtered(
                        lambda a, p=partner, ca=chain_agreement: a.partner_id == p
                        and a.unilever_rappel_group_id == ca.unilever_rappel_group_id
                        and a.year == ca.year
                    )
                    if not agreement:
                        description += "{} Grupo: {} Año: {}\n".format(
                            partner.name,
                            chain_agreement.unilever_rappel_group_id.display_name,
                            chain_agreement.year,
                        )
                        affected_records |= chain_agreement
                if description:
                    line_vals.append(
                        (
                            0,
                            0,
                            {
                                "name": "Acuerdos no encontrados similares al "
                                "de la cadena:\n{} - {}".format(
                                    chain_partner.unilever_dealer_chain,
                                    chain_partner.name,
                                ),
                                "description": description,
                                "model_name": "agreement",
                                "affected_records": affected_records.ids,
                                "context": {"default_partner_id": partner.id},
                            },
                        )
                    )
        self.line_ids = line_vals

    def process_unilever_agreement_chain_sync(self):
        """
        Set chain in agreements for commercial delivery contacts
        """
        self.line_ids = False
        ResPartner = self.env["res.partner"]
        ulv_partners = ResPartner.search(
            [
                ("unilever_dealer_chain", "!=", False),
            ]
        )
        ulv_chain_partners = ulv_partners.filtered(
            lambda p: p.unilever_ref and p.unilever_ref == str(p.unilever_dealer_chain)
        )
        line_vals = []
        for chain_partner in ulv_chain_partners:
            all_partners = ResPartner.search(
                [
                    ("unilever_dealer_chain", "=", chain_partner.unilever_dealer_chain),
                ],
            )
            if len(all_partners) == 1:
                continue
            agreements = self.env["agreement"].search(
                [
                    ("agreement_type", "=", "DTO"),
                    ("partner_id", "in", all_partners.ids),
                    ("chain", "=", False),
                    ("anual_discount_percent", "!=", False),
                ]
            )
            affected_records = agreements.browse()
            description = ""
            for agreement in agreements:
                description += "{} Grupo: {} Año: {}\n".format(
                    agreement.partner_id.name,
                    agreement.unilever_rappel_group_id.display_name,
                    agreement.year,
                )
                affected_records |= agreement
            if description:
                line_vals.append(
                    (
                        0,
                        0,
                        {
                            "name": "Acuerdos sin marca cadena:\n"
                            "{} - {}".format(
                                chain_partner.unilever_dealer_chain, chain_partner.name
                            ),
                            "description": description,
                            "model_name": "agreement",
                            "affected_records": affected_records.ids,
                            "context": {"default_partner_id": agreement.partner_id.id},
                        },
                    )
                )
        self.line_ids = line_vals

    def action_check(self):
        self.ensure_one()
        getattr(self, f"process_{self.check_type}")()


class DataIntegrityLineWiz(models.TransientModel):
    _name = "data.integrity.line.wiz"
    _description = "Data integrity check wizard lines"

    wizard_id = fields.Many2one(
        comodel_name="data.integrity.wiz",
        readonly=True,
    )
    name = fields.Text(readonly=True)
    description = fields.Text(readonly=True)
    model_name = fields.Char()
    domain = fields.Char(compute="_compute_domain")
    context = fields.Char()
    affected_records = fields.Char()

    def _compute_domain(self):
        self.domain = [
            ("id", "in", safe_eval(self.affected_records)),
        ]

    def action_open_records(self):
        if self.model_name == "res.partner":
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "base.action_partner_form"
            )
        elif self.model_name == "agreement":
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "agreement.agreement_action"
            )
        action["domain"] = self.domain
        action["context"] = self.context or {}
        return action
