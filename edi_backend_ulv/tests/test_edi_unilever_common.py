# Copyright 2021 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from freezegun import freeze_time

from odoo.tests.common import Form, TransactionCase, tagged


@freeze_time("2022-01-01 12:00:00")
@tagged("-at_install", "post_install")
class TestEdiUnileverCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Partner = self.env["res.partner"]
        self.ProductTemplate = self.env["product.template"]
        self.Product = self.env["product.product"]
        self.ProductCategory = self.env["product.category"]
        self.AccountInvoice = self.env["account.move"]
        self.AccountInvoiceLine = self.env["account.move.line"]
        self.AccountJournal = self.env["account.journal"]
        self.EdiUnilever = self.env["edi.backend"]
        self.Agreement = self.env["agreement"]
        self.AgreementType = self.env["agreement.type"]
        self.AgreementColType = self.env["edi.unilever.agreement.col.type"]
        self.UnileverRappelGroup = self.env["unilever.rappel.group"]
        self.AgreementCondition = self.env["edi.unilever.agreement.condition"]
        self.UnileverCategory = self.env["edi.unilever.category"]
        self.UnileverCompetency = self.env["edi.unilever.competency"]
        self.SaleOrder = self.env["sale.order"].with_context(
            prevent_onchange_quantity=True
        )
        self.pricelist = self.env["product.pricelist"].create(
            {
                "name": "pricelist for tests",
                "currency_id": self.env.company.currency_id.id,
            }
        )
        # Data needed to send some files to Unilever
        self.env.company.write(
            {
                "unilever_dealer": "179",
                "unilever_comunication_code": "179",
            }
        )
        self.category_all = self.env.ref("product.product_category_all")
        self.categ_1 = self.ProductCategory.create(
            {"parent_id": self.category_all.id, "name": "Category 1"}
        )
        self.categ_2 = self.ProductCategory.create(
            {"parent_id": self.category_all.id, "name": "Category 2"}
        )
        # Crate some rappel groups
        self._create_rappel_group()
        # Create some products
        self._create_products()
        # Create agreement types
        self._create_agreement_type()
        # Create agreement condition for GIRA agreements
        self.agreement_condition_gira = self._create_agreement_condition(
            condition_type="GIRA"
        )
        # Create some data to be used in partners
        self._create_unilever_competency()
        self._create_unilever_category()
        # Create some partners
        self._create_partners()
        # Create agreements
        self.agreement_dto = self._create_agreement(agreement_type="DTO")
        self.agreement_gira = self._create_agreement(agreement_type="GIRA")
        self.agreement_col = self._create_agreement(agreement_type="COL")

    def _create_products(self):
        self.product_1_IM = self.Product.create(
            {
                "name": "Product test 1",
                "categ_id": self.categ_1.id,
                "list_price": 1000.00,
                "unilever_rappel_group_id": self.rappel_group_IM.id,
            }
        )
        self.product_2_BJ = self.Product.create(
            {
                "name": "Product test 2",
                "categ_id": self.categ_2.id,
                "list_price": 2000.00,
                "unilever_rappel_group_id": self.rappel_group_BJ.id,
            }
        )

    def _create_agreement_type(self):
        agreement_types = ["COL", "POL", "DTO", "GIRA"]
        for agreement_type in agreement_types:
            vals = {"domain": "sale", "code": agreement_type}
            if agreement_type == "DTO":
                vals.update(
                    {
                        "name": "Descuentos a clientes concesionario",
                        "is_rebate": True,
                    }
                )
            if agreement_type == "POL":
                vals["name"] = "Política de turismo y liquidaciones"
            if agreement_type == "COL":
                vals["name"] = "Acuerdos preferentes"
            if agreement_type == "GIRA":
                vals["name"] = "Descuento GIRA"
            setattr(
                self,
                "agreement_type_%s" % agreement_type,
                self.AgreementType.create(vals),
            )

    def _create_rappel_group(self):
        self.rappel_group_H = self.UnileverRappelGroup.create(
            {
                "name": "Helado",
                "code": "G-110",
                "unilever_ref": "H",
            }
        )
        self.rappel_group_BJ_G = self.UnileverRappelGroup.create(
            {
                "name": "Ben & Jerry (Group)",
                "code": "G-103",
            }
        )
        self.rappel_group_IM = self.UnileverRappelGroup.create(
            {
                "name": "Impulso",
                "parent_id": self.rappel_group_H.id,
                "code": "110",
                "unilever_ref": "IM",
            }
        )
        self.rappel_group_RE = self.UnileverRappelGroup.create(
            {
                "name": "Restauracion",
                "parent_id": self.rappel_group_H.id,
                "code": "111",
                "unilever_ref": "RE",
            }
        )
        self.rappel_group_BJ = self.UnileverRappelGroup.create(
            {
                "name": "Ben & Jerry",
                "parent_id": self.rappel_group_BJ_G.id,
                "code": "103",
                "unilever_ref": "BJ",
            }
        )

    def _create_agreement_condition(self, condition_type="GIRA"):
        condition_form = Form(self.AgreementCondition)
        condition_form.condition_type = condition_type
        condition_form.name = "%s agreement condition" % condition_type
        condition_form.code = "809"
        condition_form.start_date = "2022-01-01"
        condition_form.end_date = "2022-12-31"
        with condition_form.line_ids.new() as line_form:
            line_form.product_id = self.product_1_IM
            line_form.condition_price = 20.00
            line_form.condition_discount = 50.00
        with condition_form.line_ids.new() as line_form:
            line_form.product_id = self.product_2_BJ
            line_form.condition_price = 30.00
            line_form.condition_discount = 10.00
        return condition_form.save()

    def _create_agreement(self, agreement_type="DTO"):
        agreement_form = Form(self.Agreement, "edi_backend_ulv.agreement_form")
        agreement_form.name = "Agreement for test %s" % agreement_type
        agreement_form.code = "AG-TEST-%s" % agreement_type
        agreement_form.agreement_type_id = self.env.ref(
            f"edi_backend_ulv.{agreement_type}"
        )
        agreement_form.partner_id = self.partner_1_delivery_1
        agreement_form.start_date = "2022-01-01"
        if agreement_type == "DTO":
            agreement_form.invoice_discount = 25
            agreement_form.unilever_rappel_group_id = self.rappel_group_BJ
        if agreement_type == "GIRA":
            agreement_form.agreement_condition_id = self.agreement_condition_gira
        if agreement_type == "COL":
            agreement_col_type = self.AgreementColType.create(
                {
                    "name": "Actividad promocional",
                    "unilever_ref": "P",
                    "unilever_rappel_group_id": self.rappel_group_IM.id,
                }
            )
            agreement_form.col_type_id = agreement_col_type
            agreement_form.unilever_rappel_group_id = self.rappel_group_IM
        return agreement_form.save()

    def _archive_agreements_distinct_from(self, partner, agreement_type):
        agreements = self.Agreement.search(
            [
                ("partner_id", "=", partner.id),
                ("agreement_type_id.code", "!=", agreement_type),
            ]
        )
        agreements.active = False

    def _create_unilever_category(self):
        self.unilever_category_hotel = self.UnileverCategory.create(
            {
                "name": "Hoteles",
                "code": "11",
            }
        )

    def _create_unilever_competency(self):
        self.unilever_competency_nestle = self.UnileverCompetency.create(
            {
                "name": "Nestle",
                "code": "N",
            }
        )

    def _create_partners(self):
        common_vals = {
            "unilever_category_id": self.unilever_category_hotel.id,
            "unilever_competency_id": self.unilever_competency_nestle.id,
            "unilever_high_competency_id": self.unilever_competency_nestle.id,
            "unilever_seasonality": "yearly",
            "property_product_pricelist": self.pricelist.id,
        }
        self.partner_1 = self.Partner.create(
            dict(
                {
                    "name": "Test Partner 1",
                    "ref": "P-1",
                    "comercial": "Partner comercial name",
                    "unilever_partner_type": "C",
                    "unilever_ref": "9000242",
                    "unilever_local_code": "158",
                },
                **common_vals,
            )
        )
        self.partner_1_delivery_1 = self.Partner.create(
            dict(
                {
                    "name": "Test Partner 1 Delivery 1",
                    "ref": "P-1-D-1",
                    "parent_id": self.partner_1.id,
                    "type": "delivery",
                    "unilever_ref": "774",
                    "unilever_local_code": "774",
                },
                **common_vals,
            )
        )
        self.partner_2 = self.Partner.create(
            dict({"name": "Test Partner 2", "ref": "P-2"}, **common_vals)
        )
