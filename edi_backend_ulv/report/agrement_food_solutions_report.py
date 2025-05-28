# Copyright 2023 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from psycopg2.sql import SQL, Identifier

from odoo import fields, models, tools


class AgreementFoodSolutions(models.Model):
    _name = "agreement.food.solutions.report"
    _description = "Food Solution Agreements Report"
    _auto = False
    _rec_name = "signature_date"
    _order = "signature_date, id"

    signature_date = fields.Date(readonly=True)
    partner_id = fields.Many2one("res.partner")
    unilever_rappel_group_id = fields.Many2one("unilever.rappel.group")
    agreement_type_id = fields.Many2one("agreement.type")
    product_id = fields.Many2one("product.template")
    invoice_discount = fields.Float(readonly=True)
    start_date = fields.Date(readonly=True)
    end_date = fields.Date(readonly=True)
    unilever_participation_percent = fields.Float(readonly=True)

    def _select(self):
        return """
            SELECT
                CONCAT(ag.id::varchar, pt.id)::bigint AS id,
                ag.signature_date AS signature_date,
                ag.partner_id AS partner_id,
                ag.unilever_rappel_group_id AS unilever_rappel_group_id,
                ag.agreement_type_id AS agreement_type_id,
                pt.id AS product_id,
                ag.invoice_discount AS invoice_discount,
                ag.start_date AS start_date,
                ag.end_date AS end_date,
                ag.unilever_participation_percent AS unilever_participation_percent
            FROM agreement ag
                RIGHT JOIN product_template pt ON (
                    pt.unilever_rappel_group_id = ag.unilever_rappel_group_id
                        AND pt.active = true
                )
            WHERE ag.active = true
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = SQL("CREATE or REPLACE VIEW {} as ({})")
        # pylint: disable=sql-injection
        self.env.cr.execute(
            query.format(
                Identifier(self._table),
                SQL(self._select()),
            )
        )
