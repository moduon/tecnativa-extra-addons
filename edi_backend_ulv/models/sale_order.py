#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Commercial Entity",
        related="partner_id.commercial_partner_id",
        store=True,
        index=True,
    )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    unilever_agreement_id = fields.Many2one(
        comodel_name="agreement",
        string="UL Agreement",
    )
    commercial_partner_id = fields.Many2one(
        related="order_id.commercial_partner_id",
        readonly=True,
    )
    company_group_id = fields.Many2one(
        related="order_id.company_group_id",
        readonly=True,
    )

    def _match_ul_condition(self, filter_agreements):
        agreement = filter_agreements.filtered(
            lambda x: self.product_id in x.product_ids
        )
        if agreement:
            return agreement
        agreement = filter_agreements.filtered(
            lambda x: x.product_subgroup_id == self.product_id.categ_id
        )
        if agreement:
            return agreement
        agreements_cat = filter_agreements.filtered(
            lambda x: x.product_group_id and not x.product_subgroup_id
        )
        for agreement_cat in agreements_cat:
            categories = self.env["product.category"].search(
                [("id", "child_of", agreement_cat.product_group_id.id)]
            )
            if self.product_id.categ_id in categories:
                agreement = agreement_cat
                break
        if agreement:
            return agreement
        if self.product_id.unilever_rappel_group_id:
            agreement = filter_agreements.filtered(
                lambda x: x.agreement_type in ("DTO", "COL")
                and (
                    x.unilever_rappel_group_id
                    == self.product_id.unilever_rappel_group_id
                )
            )
            if agreement:
                return agreement
            agreement = filter_agreements.filtered(
                lambda x: (
                    x.agreement_type in ("DTO", "COL")
                    and x.unilever_rappel_group_id
                    and x.unilever_rappel_group_id
                    == self.product_id.unilever_rappel_group_id.parent_id
                )
            )
            if agreement:
                return agreement
        return agreement

    def _search_ul_agreement(self):
        domain = [
            ("agreement_type", "in", ("POL", "GIRA", "DTO", "COL")),
            ("start_date", "<=", self.order_id.date_order),
            "|",
            ("end_date", ">=", self.order_id.date_order),
            ("end_date", "=", False),
        ]
        commercial_partner = self.order_id.partner_id.commercial_partner_id
        company_group = self.order_id.partner_id.company_group_id
        if company_group:
            domain.extend(["|", ("partner_id", "=", company_group.id)])
        domain.append(("partner_id", "child_of", commercial_partner.id))
        Agreement = self.env["agreement"]
        agreement = Agreement.browse()
        agreements = Agreement.search(
            domain, order="partner_id DESC, invoice_discount DESC"
        )
        if not agreements:
            return agreement
        for agreement_type in ["POL", "GIRA", "DTO", "COL"]:
            filter_agreements = agreements.filtered(
                lambda x, at=agreement_type: x.agreement_type == at
            )
            if not filter_agreements:
                continue

            # TODO: Move code to process after specific agreements
            # Search agreements without partner, this apply to all
            global_agreements = filter_agreements.filtered(lambda x: not x.partner_id)
            agreement = self._match_ul_condition(global_agreements)
            if agreement:
                return agreement[:1]

            # Search agreements for partner or his parent or chain and keep
            # order of records: partner --> parent --> chain partner
            order_partner = self.order_id.partner_id
            for partner in order_partner.get_ancestor_and_company_group_partners():
                partner_agreements = filter_agreements.filtered(
                    lambda x, p=partner: x.partner_id == p
                )
                agreement = self._match_ul_condition(partner_agreements)
                if agreement:
                    return agreement[:1]
        return agreement[:1]

    def get_agreement_values(self):
        self.ensure_one()
        res = {}
        if self.product_id:
            agreement = self.sudo()._search_ul_agreement()
            if agreement:
                res["unilever_agreement_id"] = agreement.id
                if agreement.agreement_condition_id:
                    agreement_condition = agreement.agreement_condition_id
                    date_order = self.order_id.date_order.date()
                    if (
                        not agreement_condition.start_date
                        or agreement_condition.start_date <= date_order
                    ) and (
                        not agreement_condition.end_date
                        or agreement_condition.end_date >= date_order
                    ):
                        line = agreement.agreement_condition_id.line_ids.filtered(
                            lambda acl: acl.product_id == self.product_id
                        )[:1]
                        price = line.condition_price or agreement.agreement_price
                        discount = line.condition_discount or agreement.invoice_discount
                    else:
                        return res
                else:
                    price = agreement.agreement_price
                    discount = agreement.invoice_discount
                if price:
                    res["price_unit"] = price
                if discount:
                    res["discount"] = discount
        return res

    @api.onchange("product_id")
    def product_id_change(self):
        res = super().product_id_change()
        self.update(self.get_agreement_values())
        return res

    @api.onchange(
        "product_id", "price_unit", "product_uom", "product_uom_qty", "tax_id"
    )
    def _onchange_discount(self):
        """
        Avoid re-calculate discounts for pricelist with with_discount policy
        """
        if not self.unilever_agreement_id:
            return super()._onchange_discount()
