# Copyright 2018 Sergio Teruel - Tecnativa <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    security_price_warning = fields.Boolean(
        compute="_compute_security_price_warning",
        compute_sudo=True,
    )
    sale_product_security_price_display_raise_button = fields.Boolean(
        related="company_id.sale_product_security_price_display_raise_button"
    )

    def _compute_security_price_warning(self):
        for order in self:
            if not order.partner_id.security_price_control:
                order.security_price_warning = False
                continue
            order.security_price_warning = order.order_line.filtered(
                "security_price_warning"
            )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    security_price = fields.Float(
        compute="_compute_security_price",
        compute_sudo=True,
        digits="Product Price",
    )
    security_price_warning = fields.Boolean(
        compute="_compute_security_price_warning",
        compute_sudo=True,
    )
    # To manage in kanban view
    sale_product_security_price_display_raise_button = fields.Boolean(
        related="company_id.sale_product_security_price_display_raise_button"
    )

    @api.depends("product_id")
    def _compute_security_price(self):
        # Includes elaboration cost if it is set in line
        elaboration_installed = True if "elaboration_ids" in self else False
        for line in self:
            line.security_price = line.product_id.security_price
            if elaboration_installed:
                line.security_price += sum(
                    line.sudo().mapped("elaboration_ids.product_id.standard_price")
                )

    @api.depends("order_partner_id", "product_id", "price_reduce", "security_price")
    def _compute_security_price_warning(self):
        precision = self.env["decimal.precision"].precision_get("Product Price")
        if not self[:1].order_id.partner_id.security_price_control:
            # If partner has not check the security price control we avoid to evaluate
            # so lines
            self.security_price_warning = False
        else:
            for line in self:
                if line.product_id.security_price_control:
                    line.security_price_warning = bool(
                        float_compare(
                            line.price_reduce,
                            line.security_price,
                            precision_digits=precision,
                        )
                        == -1
                    )
                else:
                    line.security_price_warning = False

    def write(self, vals):
        """Ensure that the salesman do not change price or discount in order
        lines which already has been confirmed after a tier validation request.
        In this case is the security price.
        """
        res = super().write(vals)
        if self.env.context.get(
            "skip_security_price_lock", False
        ) or self.env.user.has_group("sales_team.group_sale_manager"):
            return res
        if "price_unit" in vals or "discount" in vals:
            for line in self.filtered(
                lambda ln: ln.order_id.state not in ["draft", "sent"]
                and ln.order_id.partner_id.sudo().security_price_control
                and ln.product_id.sudo().security_price_control
            ):
                if line.security_price_warning:
                    raise ValidationError(
                        _("You can not update price below the safety price")
                    )
        return res

    def rise_up_to_security_price(self):
        self.ensure_one()
        if self.security_price > self.price_reduce:
            if self.discount == 100:
                self.price_unit = self.security_price
                self.discount = 0.0
            self.price_unit = (self.security_price * 100) / (100 - self.discount)
