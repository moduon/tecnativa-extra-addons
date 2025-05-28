# Copyright 2021 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from freezegun import freeze_time

from odoo.tests.common import Form, tagged

from .test_edi_unilever_common import TestEdiUnileverCommon


@freeze_time("2022-01-01 12:00:00")
@tagged("-at_install", "post_install")
class TestEdiUnileverSale(TestEdiUnileverCommon):
    # The agreement order applied on sale order when a customer has distinct
    # agreement types is: ["POL", "GIRA", "DTO", "COL"]
    # So the first test to pass is check what agreement has been applied on
    # sale order. For complete the test for each agreement we should be archive
    # the other customer agreements.
    def test_agreement_on_sale_applied(self):
        sale_form = Form(self.SaleOrder)
        sale_form.partner_id = self.partner_1_delivery_1
        with sale_form.order_line.new() as line_form:
            line_form.product_id = self.product_1_IM
            self.assertEqual(line_form.unilever_agreement_id, self.agreement_gira)

    def test_apply_gira_agreement_on_sale(self):
        # If a customer has a GIRA agreement when user does a sale for a
        # product included in this agreement, the price and discount have
        # been informed on GIRA agreement
        self._archive_agreements_distinct_from(self.partner_1_delivery_1, "GIRA")
        sale_form = Form(self.SaleOrder)
        sale_form.partner_id = self.partner_1_delivery_1
        with sale_form.order_line.new() as line_form:
            line_form.product_id = self.product_1_IM
            self.assertEqual(line_form.discount, 50.00)
            self.assertEqual(line_form.price_unit, 20.00)
        with sale_form.order_line.new() as line_form:
            line_form.product_id = self.product_2_BJ
            self.assertEqual(line_form.discount, 10.00)
            self.assertEqual(line_form.price_unit, 30.00)

    def test_apply_dto_agreement_on_sale(self):
        # Only the discount should be applied on line of BJ product
        self._archive_agreements_distinct_from(self.partner_1_delivery_1, "DTO")
        sale_form = Form(self.SaleOrder)
        sale_form.partner_id = self.partner_1_delivery_1
        with sale_form.order_line.new() as line_form:
            line_form.product_id = self.product_2_BJ
            self.assertEqual(line_form.discount, self.agreement_dto.invoice_discount)
        with sale_form.order_line.new() as line_form:
            line_form.product_id = self.product_1_IM
            self.assertEqual(line_form.discount, 0.0)
