# Copyright 2022 Tecnativa - Sergio Teruel
# Copyright 2022 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl
from odoo import fields, models


class EdiBackendMixin(models.AbstractModel):
    _name = "edi.backend.mixin"
    _description = "EDI Backend mixin for records"

    """
    Backend providers

    In order to add your use the mixin with another provider:

    1. Create your own module and _inherit `edi.backend.mixin`
    2. Extend the selection of the field `provider` in `edi.backend` with a pair
       ('<my_provider>', 'My Provider')
    3. Add your methods in this mixin:
       <my_provider>_action_backend_sent
       <my_provider>_action_backend_not_sent
       <my_provider>_action_backend_sent_error
       <my_provider>_action_backend_cancelled
    """

    backend_state_base = fields.Selection(
        selection=[
            ("not_sent", "Not sent"),
            ("sent", "Sent"),
            ("sent_error", "Errors"),
            ("cancelled", "Cancelled"),
        ],
        string="Backend state",
        help="Indicates the state of the Backend send state",
        compute="_compute_backend_state_base",
        readonly=False,
        store=True,
    )

    def _compute_backend_state_base(self):
        self.backend_state_base = "not_sent"

    def base_action_backend_sent(self):
        self.write({"backend_state_base": "sent"})

    def base_action_backend_not_sent(self):
        self.write({"backend_state_base": "not_sent"})

    def base_action_backend_sent_error(self):
        self.write({"backend_state_base": "sent_error"})

    def base_action_backend_cancelled(self):
        self.write({"backend_state_base": "cancelled"})
