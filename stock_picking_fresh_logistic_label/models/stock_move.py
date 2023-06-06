# Copyright 2022 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class ResConfigSettings(models.Model):
    _inherit = "stock.move"

    def filter_lines_for_logistic_labels(self):
        domain = [("id", "in", self.ids)]
        if self.env.company.logistic_label_domain:
            domain = expression.AND(
                [domain, safe_eval(self.env.company.logistic_label_domain)]
            )
        # Used search because filtered_domain is not able to manage all types of domains
        return self.search(domain)
