# Copyright 2021 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, tagged

from .test_edi_unilever_common import TestEdiUnileverCommon


@tagged("-at_install", "post_install")
class TestEdiUnileverFile(TestEdiUnileverCommon):
    # This tests coverage the date that we must send to Unilever
    # This file are been generated from edi unilever backends and they are:

    # Fichero clientes (CLI)
    def test_backend_cli_file(self):
        backend_form = Form(self.EdiUnilever)
        backend_form.name = "Clientes"
        backend_form.code = "CLI"
        backend_form.provider = "ulv"
        backend_form.communication_type = "ftp"
        backend_form.action_type = "export"
        backend_form.model_id = self.env.ref("base.model_res_partner")
        backend_form.filter_domain = [
            "&",
            ("unilever_ref", "!=", False),
            ("unilever_state", "=", "not_sent"),
        ]
        date_field = self.env["ir.model.fields"].search(
            [
                ("model_id.model", "=", "res.partner"),
                ("name", "=", "write_date"),
            ]
        )
        backend_form.date_field = date_field
        backend_form.export_config_id = self.env.ref(
            "edi_backend_ulv.edi_unilever_export_config_cli_l0"
        )
        backend = backend_form.save()
        backend.action_export()
        self.assertTrue(backend.data)
        self.assertEqual(backend.history_count, 1)
        self.assertEqual(backend.file_name, "179CLI0002.0001")

    # Fichero Descuentos a clientes concesionario (DTO)
    def test_backend_dto_file(self):
        backend_form = Form(self.EdiUnilever)
        backend_form.name = "Descuentos a clientes concesionario"
        backend_form.code = "DTO"
        backend_form.provider = "ulv"
        backend_form.communication_type = "ftp"
        backend_form.action_type = "export"
        backend_form.model_id = self.env.ref(
            "edi_backend_ulv.model_unilever_agreement_communication"
        )
        backend_form.filter_domain = [
            ("agreement_id.agreement_type", "=", "DTO"),
            ("unilever_state", "=", "not_sent"),
            ("agreement_id.unilever_rappel_group_id", "!=", False),
        ]
        date_field = self.env["ir.model.fields"].search(
            [
                ("model_id.model", "=", "agreement"),
                ("name", "=", "write_date"),
            ]
        )
        backend_form.date_field = date_field
        backend_form.export_config_id = self.env.ref(
            "edi_backend_ulv.edi_unilever_export_config_dto_l0"
        )
        backend = backend_form.save()
        backend.action_export()
        self.assertTrue(backend.data)
        self.assertEqual(backend.history_count, 1)
        self.assertEqual(backend.file_name, "179DTO0001.0001")

    # Fichero Acuerdos preferentes (COL)
    def test_backend_col_file(self):
        backend_form = Form(self.EdiUnilever)
        backend_form.name = "Actividad promocional"
        backend_form.code = "COL"
        backend_form.provider = "ulv"
        backend_form.communication_type = "ftp"
        backend_form.action_type = "export"
        backend_form.model_id = self.env.ref("agreement.model_agreement")
        backend_form.filter_domain = [
            ("agreement_type", "=", "COL"),
            ("unilever_state", "=", "not_sent"),
            ("move_type", "!=", "B"),
        ]
        date_field = self.env["ir.model.fields"].search(
            [
                ("model_id.model", "=", "agreement"),
                ("name", "=", "write_date"),
            ]
        )
        backend_form.date_field = date_field
        backend_form.export_config_id = self.env.ref(
            "edi_backend_ulv.edi_unilever_export_config_col_l0"
        )
        backend = backend_form.save()
        backend.action_export()
        self.assertTrue(backend.data)
        self.assertEqual(backend.history_count, 1)
        self.assertEqual(backend.file_name, "179COL0001.0001")
