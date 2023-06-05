# Copyright 2020 Sergio Teruel - Tecnativa

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import Form, TransactionCase


class TestStockReportStockOut(TransactionCase):
    def setUp(self):
        super().setUp()
        self.stock_loc = self.env.ref("stock.stock_location_stock")
        self.customer_loc = self.env.ref("stock.stock_location_customers")
        self.uom_unit = self.env.ref("uom.product_uom_unit")

        self.Partner = self.env["res.partner"]
        self.Product = self.env["product.product"]
        self.StockPicking = self.env["stock.picking"]
        self.StockMove = self.env["stock.move"]
        self.StockQuant = self.env["stock.quant"]
        self.StockOutWizard = self.env["stock.report.stock.out.wiz"]
        # Set external_report_layout setting in main company
        self.env.company.external_report_layout_id = self.env.ref(
            "web.external_layout_standard"
        )
        # Set to cancel all moves in this transaction for simplify tests.
        self.StockMove.search([]).write({"state": "cancel"})
        self.partner = self.Partner.create(
            {
                "name": "partner for test",
            }
        )

        self.product1 = self.Product.create(
            {
                "type": "product",
                "name": "product1",
            }
        )
        self.product2 = self.Product.create(
            {
                "type": "product",
                "name": "product2",
            }
        )
        self.product3 = self.Product.create(
            {
                "type": "product",
                "name": "product3",
            }
        )
        self.StockQuant.create(
            {
                "product_id": self.product1.id,
                "location_id": self.stock_loc.id,
                "quantity": 100.00,
            }
        )
        self.StockQuant.create(
            {
                "product_id": self.product2.id,
                "location_id": self.stock_loc.id,
                "quantity": 100.00,
            }
        )

        self.products = self.product1 + self.product2 + self.product3
        self.picking = self.create_simple_picking(self.products)
        self.picking.action_confirm()
        self.picking.action_assign()

    def create_simple_picking(self, products):
        # The 'planned_picking' context key ensures that the picking
        # will be created in the 'draft' state (no autoconfirm)
        return self.StockPicking.with_context(planned_picking=True).create(
            {
                "picking_type_id": self.ref("stock.picking_type_out"),
                "location_id": self.stock_loc.id,
                "location_dest_id": self.customer_loc.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test move",
                            "date": fields.Date.today(),
                            "product_id": product.id,
                            "product_uom": self.ref("uom.product_uom_unit"),
                            "product_uom_qty": 200.00
                            if product == self.product2
                            else 100.00,
                            "location_id": self.stock_loc.id,
                            "location_dest_id": self.customer_loc.id,
                        },
                    )
                    for product in products
                ],
            }
        )

    def test_print_report(self):
        with Form(self.StockOutWizard) as wizard:
            wizard.date_from = fields.Date.today()
        wiz = wizard.save()
        action = wiz.action_print_report()
        products_stock_out = self.StockMove.browse(action["data"]["doc_ids"]).mapped(
            "product_id"
        )
        self.assertNotIn(self.product1, products_stock_out)

    def test_open_stock_move_view(self):
        with Form(self.StockOutWizard) as wizard:
            wizard.date_from = fields.Date.today()
        wiz = wizard.save()
        action = wiz.action_open_view_moves()
        products_stock_out = self.StockMove.browse(action["domain"][0][2]).mapped(
            "product_id"
        )
        self.assertNotIn(self.product1, products_stock_out)

    def test_send_summary_email(self):
        with Form(self.StockOutWizard) as wizard:
            wizard.date_from = fields.Date.today()
            wizard.date_to = fields.Date.today() + relativedelta(days=1)
        wiz = wizard.save()
        self.assertTrue(wiz.stock_out_summary_send())

    def test_moves_stock_out_after_picking_validation(self):
        for move_line in self.picking.move_ids:
            move_line.quantity_done = move_line.reserved_availability
        self.picking._action_done()
        # Cancel the backorder created
        self.picking.backorder_ids.action_cancel()

        with Form(self.StockOutWizard) as wizard:
            wizard.date_from = fields.Date.today()
        wiz = wizard.save()
        moves = wiz._get_moves_stock_out(wiz.date_from)
        my_moves = moves.filtered(lambda mv: mv.product_id in self.products)
        self.assertEqual(len(my_moves), 0)
        move_product2 = my_moves.filtered(lambda mv: mv.product_id == self.product2)
        self.assertEqual(move_product2.product_uom_qty, 0.0)
        move_product3 = my_moves.filtered(lambda mv: mv.product_id == self.product3)
        self.assertEqual(move_product3.product_uom_qty, 0.0)

    def test_raises_for_non_exists_stock_out(self):
        with Form(self.StockOutWizard) as wizard:
            wizard.date_from = fields.Date.today() + relativedelta(days=5)
        wiz = wizard.save()
        with self.assertRaises(UserError):
            wiz.action_print_report()
        with self.assertRaises(UserError):
            wiz.stock_out_summary_send()
