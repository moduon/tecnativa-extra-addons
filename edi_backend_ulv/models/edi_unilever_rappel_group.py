#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class UnileverRappelGroup(models.Model):
    _name = "unilever.rappel.group"
    _description = "Unilever rappel group"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = "name"
    _order = "parent_path"

    name = fields.Char("Name", index=True, required=True, translate=True)
    parent_id = fields.Many2one(
        "unilever.rappel.group", "Parent group", index=True, ondelete="cascade"
    )
    child_id = fields.One2many("unilever.rappel.group", "parent_id", "Child groups")
    parent_path = fields.Char(index=True)
    code = fields.Char(string="Rappel group code")
    unilever_ref = fields.Char(string="UL Rappel group", size=2)
    grouped_group = fields.Boolean(string="Grouped group")
    grouped_subgroup = fields.Boolean(
        string="Grouped subgroup",
        default=True,
    )

    @api.constrains("parent_id")
    def _check_group_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("Error ! You cannot create recursive groups."))
        return True

    def name_get(self):
        # Prefetch the fields used by the `name_get`, so `browse`
        # doesn't fetch other fields
        self.read(["name", "code"])
        return [
            (
                group.id,
                f"{group.code and '[' + group.code + '] ' or ''}"
                f"{group.unilever_ref and '[' + group.unilever_ref + '] ' or ''}"
                f"{group.name}",
            )
            for group in self
        ]

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("code", "=", name), ("name", operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ["&", "!"] + domain[1:]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()
