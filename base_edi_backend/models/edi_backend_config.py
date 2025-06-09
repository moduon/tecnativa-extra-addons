# Copyright 2022 Tecnativa - Sergio Teruel
# Copyright 2022 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl
from odoo import fields, models


class EdiBackendConfig(models.Model):
    _name = "edi.backend.config"
    _description = "EDI Backend Config"
    _order = "name"

    name = fields.Char()
    model_number = fields.Char(string="Model number", size=3)
    model_id = fields.Many2one(comodel_name="ir.model", string="Odoo model")
    active = fields.Boolean(default=True)
    date_start = fields.Date(string="Starting date")
    date_end = fields.Date(string="Ending date")
    config_line_ids = fields.One2many(
        comodel_name="edi.backend.config.line",
        inverse_name="export_config_id",
        string="Lines",
    )
    filler_zero_with = fields.Selection(
        [("zero", "Zeros"), ("blank", "Blank")],
        string="Fill left zeros with...",
    )
    columns_definition = fields.Selection(
        [("positional", "Positional"), ("separator", "Separator")], default="positional"
    )
    separator_char = fields.Char(default=";")


class EdiBackendConfigLine(models.Model):
    _inherit = "aeat.model.export.config.line"
    _name = "edi.backend.config.line"
    _description = "EDI Backend Config Line"
    _order = "sequence"

    export_config_id = fields.Many2one(
        comodel_name="edi.backend.config",
        string="Config parent",
        ondelete="cascade",
    )
    subconfig_id = fields.Many2one(
        comodel_name="edi.backend.config",
        string="Sub-configuration",
    )
    filler_zero_with = fields.Selection(
        [("zero", "Zeros"), ("blank", "Blank")],
        string="Filler left zeros with ...",
    )
    negative_sign = fields.Char(default="-")
    apply_separator_char = fields.Boolean(default=True)
    anonymize_value = fields.Boolean()
    key = fields.Char()
    allow_special_character = fields.Boolean()
