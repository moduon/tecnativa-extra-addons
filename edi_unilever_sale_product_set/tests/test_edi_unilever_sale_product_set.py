# Copyright 2021 Tecnativa - Carlos Roca
from odoo.exceptions import UserError
from odoo.tests import common


class TestEdiUnileverSaleProductSet(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_test = cls.env["product.product"].create(
            {
                "name": "Test",
                "list_price": 100.0,
            }
        )
        cls.set_line = cls.env["product.set.line"].create(
            {
                "product_id": cls.product_test.id,
                "quantity": 1,
                "price_unit": 20,
            }
        )
        cls.set = cls.env["product.set"].create(
            {
                "name": "Test",
                "set_line_ids": [(4, cls.set_line.id)],
                "is_ul_fill": True,
            }
        )
        cls.so_1 = cls.env.ref("sale.sale_order_6")
        cls.so_set = (
            cls.env["product.set.add"]
            .with_context(active_id=cls.so_1.id, active_model="sale.order")
            .create({"product_set_id": cls.set.id, "quantity": 1})
        )
        cls.so_set.add_set()

    def test_price_unit(self):
        order_line = self.so_1.order_line.filtered(
            lambda x: x.product_id == self.set.set_line_ids[0].product_id
        )
        order_line.ensure_one()
        self.assertEqual(order_line.price_unit, self.set_line.price_unit)

    def test_just_one_set_by_year(self):
        partner = self.env.ref("base.res_partner_1")
        so_1 = self.env["sale.order"].create(
            {"name": "Test 1", "partner_id": partner.id}
        )
        so_set_1 = (
            self.env["product.set.add"]
            .with_context(active_id=so_1.id, active_model="sale.order")
            .create({"product_set_id": self.set.id, "quantity": 1})
        )
        so_set_1.add_set()
        so_2 = self.env["sale.order"].create(
            {"name": "Test 2", "partner_id": partner.id}
        )

        so_set_2 = (
            self.env["product.set.add"]
            .with_context(active_id=so_2.id, active_model="sale.order")
            .create({"product_set_id": self.set.id, "quantity": 1})
        )
        with self.assertRaises(UserError):
            so_set_2.add_set()
