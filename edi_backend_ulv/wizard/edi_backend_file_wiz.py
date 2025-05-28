# Copyright 2023 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class EdiBackendFileWiz(models.TransientModel):
    _inherit = "edi.backend.file.wiz"

    def filter_line(self, content_line):
        # Permite no añadir la linea al fichero en caso de que no cumpla
        # alguna condicion
        code = self.env.context.get("code")
        if code == "POL-LIQ" and content_line:
            quantity = int(content_line.decode()[33:40])
            if quantity == 0:
                content_line = b""
        return content_line

    def _export_config(self, obj, export_config):
        content = super()._export_config(obj, export_config)
        content = self.filter_line(content)
        return content
