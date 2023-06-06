# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestSaleSecurityPrice(TransactionCase):
    def setUp(self):
        super().setUp()
        group = self.env.ref("product.group_discount_per_so_line")
        group.users = [(4, self.env.user.id)]
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        self.Partner = self.env["res.partner"]
        self.Product = self.env["product.product"]
        self.User = self.env["res.users"]

        self.product = self.Product.create(
            {
                "name": "Product test 1",
                "list_price": 100.00,
                "standard_price": 5.00,
                "security_price_control": True,
                "security_price": 90.00,
            }
        )
        self.partner = self.Partner.create(
            {
                "name": "partner test rebate 1",
                "ref": "TST-001",
                "security_price_control": True,
            }
        )
        self.sales_admin_user = self.User.create(
            {
                "name": "Sales Administrator User",
                "login": "sales_admin_user",
                "groups_id": [(4, self.env.ref("sales_team.group_sale_manager").id)],
            }
        )
        self.salesman_user = self.User.create(
            {
                "name": "Salesman user",
                "login": "salesman_user",
                "groups_id": [(4, self.env.ref("sales_team.group_sale_salesman").id)],
            }
        )

    def _create_sale_order(self, user=False):
        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.partner
        if user:
            order_form.user_id = user
        with order_form.order_line.new() as line_form:
            line_form.product_id = self.product
            line_form.product_uom_qty = 1.0
        sale = order_form.save()
        sale.action_confirm()
        return sale

    def test_sale_order_security_price_change_allowed(self):
        sale_order = self._create_sale_order()
        sale_order.order_line.price_unit = 90.0
        self.assertEqual(sale_order.order_line.price_unit, 90.0)
        sale_order.order_line.price_unit = 100.0
        sale_order.order_line.discount = 10.00
        self.assertEqual(sale_order.order_line.price_subtotal, 90.0)

    def test_sale_order_security_price_locked(self):
        sale_order = self._create_sale_order(user=self.salesman_user)
        sale_order = sale_order.with_user(self.salesman_user.id)
        with self.assertRaises(ValidationError):
            sale_order.order_line.price_unit = 25
        with self.assertRaises(ValidationError):
            sale_order.order_line.discount = 50.00
        # Skip lock
        sale_order.with_context(
            skip_security_price_lock=True
        ).order_line.price_unit = 25
        self.assertEqual(sale_order.order_line.price_unit, 25.0)

    def test_sale_order_security_price_by_user(self):
        # Administrator sales user can update the price always
        sale_order = self._create_sale_order(user=self.salesman_user)
        with self.assertRaises(ValidationError):
            sale_order.with_user(self.salesman_user.id).order_line.price_unit = 25
        sale_order.with_user(self.sales_admin_user.id).order_line.price_unit = 25
        self.assertEqual(sale_order.order_line.price_unit, 25.0)

    def test_raise_unit_price_to_product_security_price(self):
        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.partner
        with order_form.order_line.new() as line_form:
            line_form.product_id = self.product
            line_form.price_unit = 70.0
        sale = order_form.save()
        self.assertEqual(sale.order_line.price_unit, 70.0)
        # simulate clic on button in the line to raise the unit price
        # to the product security price
        sale.order_line.rise_up_to_security_price()
        self.assertEqual(sale.order_line.price_unit, 90.0)
        self.assertEqual(sale.order_line.price_reduce, 90.0)
        # Add a percent and rise up the unit price until
        # price_reduce is the security price
        with Form(sale) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.discount = 10
        sale.order_line.rise_up_to_security_price()
        self.assertEqual(sale.order_line.price_unit, 100.0)
        self.assertEqual(sale.order_line.price_reduce, 90.0)
        # Add a percent and rise up the unit price until
        # price_reduce is the security price
        with Form(sale) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.discount = 100
        sale.order_line.rise_up_to_security_price()
        self.assertEqual(sale.order_line.discount, 0.0)

    def test_sale_order_security_price_percent(self):
        self.product.write(
            {
                "security_price_method": "percent",
                "security_price_percent": 30,
            }
        )
        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.partner
        with order_form.order_line.new() as line_form:
            line_form.product_id = self.product
            line_form.price_unit = 6
        sale = order_form.save()
        self.assertEqual(sale.order_line.price_unit, 6)
        # simulate clic on button in the line to raise the unit price
        # to the product security price
        sale.order_line.rise_up_to_security_price()
        self.assertEqual(sale.order_line.price_unit, 7.15)

    def test_sale_order_with_diferent_rounding_method(self):
        dp = self.env.ref("product.decimal_price")
        dp.digits = 3
        self.env.company.security_price_rounding_factor = 0.005
        self.product.write(
            {
                "security_price_method": "percent",
                "security_price_percent": 30,
            }
        )
        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.partner
        with order_form.order_line.new() as line_form:
            line_form.product_id = self.product
            line_form.price_unit = 6
        sale = order_form.save()
        self.assertEqual(sale.order_line.price_unit, 6)
        # simulate clic on button in the line to raise the unit price
        # to the product security price
        sale.order_line.rise_up_to_security_price()
        self.assertAlmostEqual(sale.order_line.price_unit, 7.145, 3)

    def test_calculate_security_price_from_templates(self):
        template = self.env["product.security.price.template"].create(
            {
                "amount_from": 0,
                "amount_to": 10,
                "security_price_method": "fixed",
                "security_price": 10,
            }
        )
        self.product.product_tmpl_id.action_security_price_from_template()
        self.assertEqual(self.product.security_price, 90)
        self.product.security_price = 0
        self.product.product_tmpl_id.action_security_price_from_template()
        self.assertEqual(self.product.security_price, 15)
        self.product.security_price = 0
        template.write(
            {
                "security_price_method": "percent",
                "security_price_percent": 30,
            }
        )
        self.product.product_tmpl_id.action_security_price_from_template()
        self.assertEqual(self.product.security_price, 7.15)
