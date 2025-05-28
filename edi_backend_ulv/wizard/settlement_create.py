# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.osv import expression


class AgreementSettlementCreateWiz(models.TransientModel):
    _inherit = "agreement.settlement.create.wiz"

    unilever_settlement_type = fields.Selection(
        [
            ("not_unilever", "Not Unilever"),
            ("dto_invoice", "Dto invoice"),
            ("bonus", "Bonus"),
        ],
        default="not_unilever",
        required=True,
        string="Unilever settlement type",
    )
    minimal_total_percent = fields.Float(
        string="Minimal % to send to Unilever",
    )

    def get_agregate_fields(self):
        res = super().get_agregate_fields()
        if self.unilever_settlement_type == "dto_invoice":
            res.extend(["price_unit_signed"])
        return res

    def _target_line_domain(self, agreement_domain, agreement, line=False):
        domain = super()._target_line_domain(agreement_domain, agreement, line=line)
        if self.unilever_settlement_type == "dto_invoice":
            # Exclude invoice lines with a discount different to the agreement
            domain = expression.AND(
                [domain, [("discount", "=", agreement.invoice_discount)]]
            )
        if agreement.product_ids:
            domain = expression.AND(
                [domain, [("product_id", "in", agreement.product_ids.ids)]]
            )
        elif agreement.unilever_rappel_group_id:
            # Exclude product invoice lines into POL agreements for the same
            # customer.
            domain = expression.AND(
                [
                    domain,
                    [
                        (
                            "product_id.unilever_rappel_group_id",
                            "child_of",
                            [agreement.unilever_rappel_group_id.id],
                        ),
                    ],
                ]
            )
            exclude_agreement_domain = [
                ("agreement_type_id.code", "=", "POL"),
                (
                    "partner_id",
                    "child_of",
                    agreement.partner_id.commercial_partner_id.id,
                ),
            ]
            if self.date_from:
                exclude_agreement_domain = expression.AND(
                    [
                        exclude_agreement_domain,
                        [
                            "|",
                            ("end_date", ">=", self.date_from),
                            ("end_date", "=", False),
                        ],
                    ]
                )
            if self.date_to:
                exclude_agreement_domain = expression.AND(
                    [
                        exclude_agreement_domain,
                        [
                            "|",
                            ("start_date", "<=", self.date_to),
                            ("start_date", "=", False),
                        ],
                    ]
                )
            excluded_agreements = agreement.search(exclude_agreement_domain)
            if not excluded_agreements:
                return domain
            inv_lines = self.env["account.invoice.report"].search(domain)
            products = inv_lines.mapped("product_id")
            products_to_exclude = products.browse()
            new_sale_line = self.env["sale.order.line"].new()
            for product in products:
                new_sale_line.product_id = product
                if new_sale_line._match_ul_condition(excluded_agreements):
                    products_to_exclude |= product
            if products_to_exclude:
                domain = expression.AND(
                    [
                        domain,
                        [
                            ("product_id", "not in", products_to_exclude.ids),
                        ],
                    ]
                )
        return domain

    def get_settlement_key(self, agreement):
        list_key = []
        if agreement.chain:
            list_key.extend(["C", agreement.partner_id.company_group_id.id])
        else:
            list_key.extend(["P", agreement.partner_id.id])
        if agreement.grouped_group:
            list_key.append(-1)
        else:
            if agreement.unilever_rappel_group_id.parent_id:
                list_key.append(agreement.unilever_rappel_group_id.parent_id.id)
            else:
                list_key.append(agreement.unilever_rappel_group_id.id)
        if agreement.grouped_subgroup:
            list_key.append(-1)
        else:
            list_key.append(agreement.unilever_rappel_group_id.id)
        return tuple(list_key)

    def _prepare_settlement(self, settlement_lines):
        if self.unilever_settlement_type == "bonus":
            settlement_lines = self._post_process_settlement_lines(settlement_lines)
        vals = super()._prepare_settlement(settlement_lines)
        if vals and self.unilever_settlement_type in ["dto_invoice", "bonus"]:
            vals["unilever_settlement_type"] = self.unilever_settlement_type
            total_amount_rebate = 0.0
            for line in settlement_lines["lines"]:
                total_amount_rebate += line[2]["amount_rebate"]
                chain_partner_id = line[2].pop("chain_partner_id", False)
                if chain_partner_id:
                    vals["partner_id"] = chain_partner_id
                # Clean vals. In v13.0 you can not create keys if the field
                # is not exists
                line[2].pop("chain", False)
            vals["amount_rebate"] = total_amount_rebate
        return vals

    def _post_process_settlement_lines(self, settlement_lines):
        total_amount_invoiced = 0.0
        for line in settlement_lines["lines"]:
            total_amount_invoiced += line[2]["amount_invoiced"]

        for line in settlement_lines["lines"]:
            agreement = self.env["agreement"].browse(line[2]["agreement_id"])
            section = agreement.rebate_section_ids.filtered(
                lambda s: s.amount_from <= total_amount_invoiced <= s.amount_to
            )
            rebate = line[2]["amount_invoiced"] * section.rebate_discount / 100
            line[2].update(
                {
                    "amount_rebate": rebate,
                    "percent": section.rebate_discount,
                    "amount_from": section.amount_from,
                    "amount_to": section.amount_to,
                    "unilever_contribution_amount": (
                        agreement.company_id.currency_id.round(
                            rebate * line[2]["unilever_participation_percent"] / 100
                        )
                    ),
                }
            )
        return settlement_lines

    def _get_existing_settlement(self, domain):
        domain = expression.AND(
            [
                domain,
                [("unilever_settlement_type", "=", self.unilever_settlement_type)],
            ]
        )
        return super()._get_existing_settlement(domain)

    def _prepare_settlement_line(
        self, domain, group, agreement, line=False, section=False
    ):
        vals = super()._prepare_settlement_line(domain, group, agreement, line, section)

        partner_fields = self._settlement_line_break_fields()
        if partner_fields:
            vals["partner_id"] = group[partner_fields[0]][0]

        if self.unilever_settlement_type not in ["dto_invoice", "bonus"]:
            return vals
        vals.update(
            {
                "unilever_rappel_group_id": agreement.unilever_rappel_group_id.id,
                "unilever_participation_percent": agreement.unilever_participation_percent,  # noqa: B950 E501
            }
        )
        if agreement.chain and agreement.partner_id.company_group_id:
            vals["chain_partner_id"] = agreement.partner_id.company_group_id.id
        if self.unilever_settlement_type == "dto_invoice":
            amount_gross = agreement.company_id.currency_id.round(
                group["price_unit_signed"]
            )
            rappel = amount_gross - vals["amount_invoiced"]
            vals.update(
                {
                    "amount_gross": amount_gross,
                    "amount_to": amount_gross,
                    "percent": agreement.invoice_discount,
                    "amount_rebate": rappel,
                    "unilever_contribution_amount": agreement.company_id.currency_id.round(  # noqa: B950 E501
                        rappel * agreement.unilever_participation_percent / 100
                    ),
                }
            )
        else:
            vals.update(
                {
                    "unilever_contribution_amount": (
                        agreement.company_id.currency_id.round(
                            vals["amount_rebate"]
                            * agreement.unilever_participation_percent
                            / 100
                        )
                    ),
                    "chain": agreement.chain,
                }
            )
        return vals

    def _special_partner_domain(self, agreement, partners):
        similar_agreements = agreement.get_similar_agreements(partner_ids=partners.ids)
        partners = similar_agreements.mapped("partner_id")
        domain = []
        if partners:
            domain.append(("move_id.partner_shipping_id", "not in", partners.ids))
        return domain

    def _partner_domain(self, agreement):
        if self.unilever_settlement_type == "not_unilever":
            return super()._partner_domain(agreement)
        if agreement.partner_id.company_group_id and (
            agreement.chain
            and agreement.partner_id.company_group_id == agreement.partner_id
        ):
            domain = self._special_partner_domain(
                agreement, agreement.partner_id.unilever_child_partner_ids
            )
            domain.append(
                (
                    "move_id.partner_shipping_id.company_group_id",
                    "=",
                    agreement.partner_id.company_group_id.id,
                )
            )
            return domain
        elif agreement.partner_id.child_ids:
            domain = self._special_partner_domain(
                agreement, agreement.partner_id.child_ids
            )
            domain.append(
                ("move_id.partner_shipping_id", "child_of", agreement.partner_id.ids)
            )
            return domain
        else:
            return [("move_id.partner_shipping_id", "=", agreement.partner_id.id)]
        # elif agreement.partner_id.type == "delivery":
        #     return [("move_id.partner_shipping_id", "=", agreement.partner_id.id)]
        # else:
        #     domain = self._special_partner_domain(
        #         agreement, agreement.partner_id.child_ids
        #     )
        #     domain.append(("move_id.partner_shipping_id",
        #           "child_of", agreement.partner_id.ids))
        #     return domain

    def _prepare_agreement_domain(self):
        domain = super()._prepare_agreement_domain()
        if self.unilever_settlement_type == "dto_invoice":
            domain = expression.AND(
                [
                    domain,
                    [
                        ("invoice_discount", "!=", 0),
                        ("unilever_rappel_group_id", "!=", False),
                    ],
                ]
            )
        elif self.unilever_settlement_type == "bonus":
            domain = expression.AND(
                [
                    domain,
                    [
                        ("anual_discount_percent", "!=", False),
                        ("unilever_rappel_group_id", "!=", False),
                    ],
                ]
            )
        return domain

    def action_create_settlement(self):
        return super(
            AgreementSettlementCreateWiz,
            self.with_context(minimal_total_percent=self.minimal_total_percent),
        ).action_create_settlement()

    def _filter_settlement_lines(self, settlement_lines):
        """Filter lines amount between -1.0 and 1.0"""
        return [
            line
            for line in filter(
                lambda ln: abs(ln[2]["amount_rebate"]) >= 1.0, settlement_lines
            )
        ]

    def _settlement_line_break_fields(self):
        return ["partner_shipping_id"]
