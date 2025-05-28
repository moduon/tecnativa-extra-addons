#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
from psycopg2.sql import SQL, Identifier

from odoo import fields, models, tools


class UnileverFreshAssetReport(models.Model):
    _name = "unilever.fresh.asset.report"
    _description = "Unilever fresh asset report"
    _auto = False

    name = fields.Char("Lot", readonly=True)
    date = fields.Datetime("Date", readonly=True)
    product_id = fields.Many2one("product.product", "Product", readonly=True)
    categ_id = fields.Many2one("product.category", "Product Category", readonly=True)
    partner_id = fields.Many2one("res.partner", "Partner", readonly=True)

    def _select(self):
        select_str = """
            SELECT
                spl.name,
                spl.product_id,
                pt.categ_id,
                sub.date,
                sub.partner_id
        """
        return select_str

    def _from(self):
        from_str = """
            stock_production_lot spl
                LEFT JOIN product_product pp ON spl.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN product_category pc ON pt.categ_id = pc.id
                LEFT JOIN (SELECT sml.lot_id, sm.partner_id, sm.date
                    FROM stock_move_line sml
                        LEFT JOIN stock_move sm ON sml.move_id = sm.id
                            LEFT JOIN stock_picking_type spt ON
                                sm.picking_type_id = spt.id
                            LEFT JOIN product_product pp ON
                                sml.product_id = pp.id
                            LEFT JOIN product_template pt ON
                                pp.product_tmpl_id = pt.id
                    WHERE spt.code = 'outgoing' AND
                        sm.state = 'done' AND pc.is_unilever_mef=true
                    ORDER BY sm.date DESC LIMIT 1) AS sub
                ON sub.lot_id = spl.id
        """
        return from_str

    def _where(self):
        where_str = """
            pc.is_unilever_mef = true
        """
        return where_str

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = SQL("CREATE or REPLACE VIEW {} as ({} FROM ({}) WHERE {})")
        # pylint: disable=sql-injection
        self.env.cr.execute(
            query.format(
                Identifier(self._table),
                SQL(self._select()),
                SQL(self._from()),
                SQL(self._where()),
            )
        )
