# Copyright 2020 Tecnativa - Alexandre Díaz
# Copyright 2020 Tecnativa - Sergio Teruel
# Copyright 2021 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestProduct(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProductProduct = cls.env["product.product"]
        cls.pricelist_standard = cls.env["product.pricelist"].create(
            {
                "name": "Sale discount from cost",
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "compute_price": "formula",
                            "base": "standard_price",
                            "price_discount": -50,
                            "price_surcharge": 0.33,
                            "applied_on": "3_global",
                        },
                    ),
                ],
            }
        )
        cls.pricelist_standard_extra = cls.env["product.pricelist"].create(
            {
                "name": "Surcharge to cost extra",
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "compute_price": "formula",
                            "base": "standard_price_extra",
                            "price_discount": -50,
                            "price_surcharge": 0.33,
                            "applied_on": "3_global",
                        },
                    )
                ],
            }
        )

    def _create_product(self, cost_price=False, cost_extra=False):
        vals = {
            "name": "Product cost extra test",
        }
        if cost_price:
            vals["standard_price"] = cost_price
        if cost_extra:
            vals["amount_cost_extra"] = cost_extra
        return self.ProductProduct.create(vals)

    def _product_change_cost_price(self, product, new_price=0.00):
        vals = {}
        if new_price:
            vals["new_price"] = new_price
        product.standard_price = new_price

    def test_create_product_with_cost(self):
        """Create a product that has in vals standard_price keys."""
        product = self._create_product(cost_price=100.00)
        self.assertEqual(product.standard_price_extra, 100.00)

    def test_change_standard_price(self):
        """
        When change standard price the amount_cost_extra not has to change
        giving values from template.
        The module stock_account uses a wizard to change product cost price
        and makes standard_price field readonly in view, this behavior broken
        set a default values when user creates a product because standard_price
        always is 0.00 in create vals dictionary
        """
        product = self._create_product(cost_price=100.00)
        product.amount_cost_extra = 10.00
        self._product_change_cost_price(product, 150.00)
        self.assertEqual(product.amount_cost_extra, 10.0)
        self.assertEqual(product.standard_price_extra, 160.00)

    def test_create_product_with_cost_and_extra(self):
        """
        Create a product that has in vals standard_price and amount_cost_extra
        keys.
        """
        product = self._create_product(cost_price=100.00, cost_extra=30.00)
        self.assertEqual(product.standard_price_extra, 130.00)

    def test_change_cost_extra(self):
        product = self._create_product(cost_price=100.00, cost_extra=30.00)
        product.amount_cost_extra = 150.00
        self.assertEqual(product.standard_price_extra, 250.00)

    def test_pricelist_item_extra(self):
        """Simple pricelist item price check. Both rules surchage 33 cents
        and 50% of the given cost."""
        product = self._create_product(cost_price=100.00, cost_extra=50.00)
        price_based_on_cost = product.with_context(
            pricelist=self.pricelist_standard.id
        )._get_contextual_price()
        price_based_on_cost_extra = product.with_context(
            pricelist=self.pricelist_standard_extra.id
        )._get_contextual_price()
        self.assertAlmostEqual(price_based_on_cost, 150.33)
        self.assertAlmostEqual(price_based_on_cost_extra, 225.33)
