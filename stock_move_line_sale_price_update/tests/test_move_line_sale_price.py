# Copyright 2020 Tecnativa - Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestMoveLineSalePrice(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product Test",
                "type": "product",
            }
        )
        cls.env["stock.quant"].create(
            {
                "product_id": cls.product.id,
                "location_id": cls.warehouse.lot_stock_id.id,
                "quantity": 200.0,
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Partner Test",
            }
        )
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": cls.product.name,
                            "product_id": cls.product.id,
                            "product_uom_qty": 3,
                            "product_uom": cls.product.uom_id.id,
                            "price_unit": 100.00,
                        },
                    ),
                ],
            }
        )
        cls.sale_order_line = cls.sale_order.order_line[0]

    def test_move_line_sale_price(self):
        self.sale_order.action_confirm()
        picking = self.sale_order.picking_ids
        picking.action_assign()
        move_lines = picking.move_line_ids_without_package
        self.assertEqual(move_lines[0].sale_price_unit, 100.0)
        move_lines[0].write({"sale_price_unit": 123.0})
        self.assertEqual(self.sale_order_line.price_unit, 123.0)
