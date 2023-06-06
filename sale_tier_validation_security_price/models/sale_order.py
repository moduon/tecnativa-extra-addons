# Copyright 2018 Tecnativa - Sergio Teruel
# Copyright 2021 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from collections import defaultdict

from odoo import models


class SaleOder(models.Model):
    _inherit = "sale.order"

    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers=tiers)
        tier_reviews = tiers | self.review_ids
        if (
            not tier_reviews.filtered(lambda r: r.status == "pending")
            and "bypass_risk" not in self.env.context
        ):
            self.filtered(lambda s: s.state not in ["done", "cancel"]).with_context(
                bypass_risk=True, security_price_tier_validation=True
            ).action_confirm()
        return res

    def _rejected_tier(self, tiers=False):
        if not self.need_validation and tiers:
            ctx = self.env.context.copy()
            ctx.update({"security_price_tier_validation": True})
            tier_definitions = tiers.mapped("definition_id")
            if (
                self.env.ref(
                    "sale_tier_validation_security_price.sale_order_minimal_price_tier"
                )
                in tier_definitions
            ):
                lines_to_reject = self.order_line.filtered("security_price_warning")
                lines_to_reject.action_security_price_rejected()
            self.with_context(tier_action_rejected=True)._validate_tier(tiers)
            tier_reviews = tiers | self.review_ids
            if not tier_reviews.filtered(lambda r: r.status == "pending"):
                self.filtered(lambda s: s.state not in ["done", "cancel"]).with_context(
                    ctx
                ).action_confirm()

    def _get_accepted_notification_subtype(self):
        """When a validation tier is rejected, the sale order is confirmed
        way tier_acept method.
        With this change we can post a rejected message instead of accepted
        message.
        """
        if self.env.context.get("tier_action_rejected", False):
            return self._get_rejected_notification_subtype()
        return "base_tier_validation.mt_tier_validation_accepted"

    def _notify_accepted_reviews(self):
        if self.env.context.get("tier_action_rejected", False):
            return self._notify_rejected_review()
        return super(SaleOder, self)._notify_accepted_reviews()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def action_security_price_rejected(self):
        order_dict = defaultdict(dict)
        for line in self.filtered("security_price_warning"):
            order_dict[line.order_id][line] = (line.price_reduce, line.security_price)
            under_price = line.security_price - line.price_reduce
            if under_price < 0.0:
                continue
            line.rise_up_to_security_price()
        for order, lines_dict in order_dict.items():
            order.message_post_with_view(
                "sale_tier_validation_security_price.track_price_security_template",
                values={"lines_dict": lines_dict},
                subtype_id=self.env.ref("mail.mt_note").id,
            )
