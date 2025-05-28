# Copyright 2021 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestEdiUnileverCommon(TransactionCase):
    def test_prueba(self):
        ResPartner = self.env["res.partner"]

        partner_form = Form(ResPartner)
        partner_form.name = "Cadena partner 1"
        partner_form.is_company = True
        chain_partner = partner_form.save()
        chain_partner.company_group_id = chain_partner

        partner_form = Form(ResPartner)
        partner_form.name = "Chain delivery"
        partner_form.type = "delivery"
        partner_form.is_company = False
        # partner_form.company_group_id = chain_partner
        partner_form.parent_id = chain_partner
        partner_form.save()

        partner_form = Form(ResPartner)
        partner_form.name = "Comercial partner 1"
        partner_form.is_company = True
        partner_form.company_group_id = chain_partner
        comercial_partner = partner_form.save()

        partner_form = Form(ResPartner)
        partner_form.name = "Comercial delivery 1"
        partner_form.type = "delivery"
        partner_form.is_company = False
        # partner_form.company_group_id = chain_partner
        partner_form.parent_id = comercial_partner
        partner_form.save()

        partner_form = Form(ResPartner)
        partner_form.name = "Comercial delivery 2"
        partner_form.type = "delivery"
        partner_form.is_company = False
        # partner_form.company_group_id = chain_partner
        partner_form.parent_id = comercial_partner
        comercial_delivery_2 = partner_form.save()

        rappel_group_im = self.env["unilever.rappel.group"].browse(199)
        self.env["unilever.rappel.group"].browse(198)
        self.env["unilever.rappel.group"].browse(192)

        agreement_type_DTO = self.env["agreement.type"].browse(4)

        agreement_form = Form(self.env["agreement"], "edi_backend_ulv.agreement_form")
        agreement_form.name = "Agreement chain IM"
        agreement_form.code = agreement_form.name
        agreement_form.agreement_type_id = agreement_type_DTO
        agreement_form.partner_id = chain_partner
        agreement_form.start_date = "2021-01-01"
        agreement_form.unilever_rappel_group_id = rappel_group_im
        agreement_form.invoice_discount = 20.0
        agreement_form.save()

        agreement_form = Form(self.env["agreement"], "edi_backend_ulv.agreement_form")
        agreement_form.name = "Agreement Comercial delivery 2 IM"
        agreement_form.code = agreement_form.name
        agreement_form.agreement_type_id = agreement_type_DTO
        agreement_form.partner_id = comercial_delivery_2
        agreement_form.start_date = "2021-01-01"
        agreement_form.unilever_rappel_group_id = rappel_group_im
        agreement_form.invoice_discount = 25.0
        agreement_form.save()

        # self.env.cr.commit()
