#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
from odoo import fields, models, tools


class AgreementUnileverMefReport(models.Model):
    _name = "agreement.unilever.mef.report"
    _description = "Unilever fresh assets without agreement report"
    _auto = False

    name = fields.Char("Lot", readonly=True)
    product_id = fields.Many2one("product.product", "Product", readonly=True)
    categ_id = fields.Many2one("product.category", "Product Category", readonly=True)

    def _select(self):
        select_str = """
            SELECT
                spl.id,
                spl.name,
                spl.product_id,
                pt.categ_id
        """
        return select_str

    def _from(self):
        from_str = """
            stock_production_lot spl
                LEFT JOIN product_product pp ON spl.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN product_category pc ON pt.categ_id = pc.id
        """
        return from_str

    def _where(self):
        where_str = """
            pc.is_unilever_mef = true AND
            spl.id NOT in (
                SELECT mef_lot_id
                FROM agreement
                WHERE active=true AND
                      mef_lot_id IS NOT NULL AND
                      mef_returned_code IS NULL
            )
        """
        return where_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # pylint: disable=sql-injection
        self.env.cr.execute(
            f"""CREATE or REPLACE VIEW {self._table} as (
            {self._select()}
            FROM ( {self._from()} )
            WHERE {self._where()}
            )"""
        )
