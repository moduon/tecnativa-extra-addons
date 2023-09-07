# Copyright 2023 Tecnativa - Pilar Vargas
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestPurchaseOrderLine(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto de prueba",
                "list_price": 100.0,
                "amount_cost_extra": 10.0,
            }
        )

        cls.purchase_order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.env.ref("base.res_partner_2").id,
            }
        )

        cls.purchase_order_line = cls.env["purchase.order.line"].create(
            {
                "product_id": cls.product.id,
                "order_id": cls.purchase_order.id,
                "product_qty": 1,
                "price_unit": 90.0,
            }
        )

    def test_list_price_margin_calculation(self):
        # Ensure that the margin calculation is done correctly
        self.purchase_order_line._compute_list_price_margin()
        self.assertAlmostEqual(self.purchase_order_line.list_price_margin, 0.0)

    def test_list_price_margin_with_zero_list_price(self):
        # Verify handling of a list_price equal to zero
        self.product.write({"list_price": 0.0})
        self.purchase_order_line._compute_list_price_margin()
        self.assertEqual(self.purchase_order_line.list_price_margin, 0.0)

    def test_list_price_margin_with_positive_margin(self):
        # Verify positive margin management
        self.purchase_order_line.write({"price_unit": 80.0})
        self.purchase_order_line._compute_list_price_margin()
        self.assertAlmostEqual(self.purchase_order_line.list_price_margin, 10.0, 2)

    def test_list_price_margin_with_negative_margin(self):
        # Verify negative margin management
        self.purchase_order_line.write({"price_unit": 110.0})
        self.purchase_order_line._compute_list_price_margin()
        self.assertAlmostEqual(self.purchase_order_line.list_price_margin, -20.0, 2)
