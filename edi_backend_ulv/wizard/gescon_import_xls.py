# Copyright 2018 Sergio Teruel <sergio.teruel@tecnativa.com>
# Copyright 2018 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# pylint: disable=missing-import-error
import base64
import io
import logging
from datetime import datetime

import xlrd
from psycopg2.extensions import AsIs

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import ormcache

_logger = logging.getLogger(__name__)

try:
    from openupgradelib.openupgrade import logged_query
except ImportError:
    _logger.debug("Cannot import 'openupgradelib'.")


def set_xls_cols():
    xls_cols = {chr(i): i - 65 for i in range(65, 91)}
    xls_cols.update({f"A{chr(i)}": (i - 65) + 26 for i in range(65, 91)})
    return xls_cols


XLS_COLS = set_xls_cols()


class GesconImportWiz(models.TransientModel):
    _name = "gescon.import.wiz"

    name = fields.Char(
        string="Description",
        required=True,
    )
    import_type = fields.Selection(
        [
            ("pricelist", "Pricelist from products"),
            ("grupos_turismo", "Grupos turismo"),
            ("discounts", "Agreements - Pricelist - Items"),
            ("inventory", "Inventario de productos"),
            ("gira", "Descuentos GIRA"),
            ("change_uom", "Cambiar UOM productos"),
            ("update_supplierinfo", "Update supplierinfo product codes"),
            ("update_unilever_participation", "Update unilever participation"),
            ("archive_virginia_partners", "Archive Virginia Partners"),
            ("medios", "Medios de frío"),
            ("unilever_partner_update", "Actualizar datos de partners"),
            ("update_pol_price", "Actualizar POL prices"),
            ("unilever_partner_sync", "Comprobacion estado de partners con Unilever"),
            ("dto_rappel", "Importar acuerdos DTO - Rappel"),
            ("agreement_mef", "Importar acuerdos MEF"),
            ("agreement_consumption", "Importar consumos anteriores para acuerdos"),
            ("refund_unilever_mef", "Devolver medios unilever"),
            ("change_unilever_mef_moves_to_E", "Convertir medios de A a E"),
            ("unilever_mef_sn_to_scrap", "Desechar medios de frío"),
            (
                "unilever_uncheck_dto_settlements_lines",
                "Desmarcar lineas de liquidacion como enviadas DTO",
            ),
            (
                "match_pro_file",
                "Actualizar campo MRDR del producto a partir de unilever_ref",
            ),
        ]
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.user.company_id,
    )
    ignore_unknown_partner = fields.Boolean(default=True)
    data_file = fields.Binary(string="File to import")
    filename = fields.Char(
        string="Filename",
    )

    # @ormcache('name')
    def search_product_by_name(self, name):
        if not name:
            return False
        return (
            self.env["product.product"]
            .with_context(active_test=False)
            .search([("name", "=", name)])
            .id
        )

    @ormcache("code")
    def search_product(self, code, add_vir=True):
        if not code:
            return False
        if add_vir:
            default_code = f"VIR-{code}"
        else:
            default_code = code
        return (
            self.env["product.product"]
            .with_context(active_test=False)
            .search([("default_code", "=", default_code)])
            .id
        )

    @ormcache("code")
    def search_uom(self, code):
        if not code:
            return False
        uom_id = self.env["uom.uom"].search([("name", "=", code)]).id
        if not uom_id:
            raise UserError(_("No se ha encontrado la unidad de " f"medida {code}"))
        return uom_id

    @ormcache("code")
    def search_category(self, code):
        if not code:
            return False
        return self.env["product.category"].search([("unilever_ref", "=", code)]).id

    def _import_pricelist(self, xl_sheet):
        col_index_init = 11
        ProductProduct = self.env["product.product"]
        for row_idx in range(2, xl_sheet.nrows):  # Iterate through rows
            list_price = xl_sheet.cell(row_idx, col_index_init).value
            for i in range(1, 6):
                price = xl_sheet.cell(row_idx, col_index_init + i).value
                if price and (price != list_price):
                    product = ProductProduct.browse(
                        self.search_product(int(xl_sheet.cell(row_idx, 0).value))
                    )
                    pricelist = self.env.ref(f"edi_backend_ulv.pricelist_gescon_{i}")
                    pricelist.item_ids = [
                        (
                            0,
                            0,
                            {
                                "applied_on": "1_product",
                                "product_tmpl_id": product.product_tmpl_id.id,
                                "compute_price": "fixed",
                                "fixed_price": price,
                            },
                        )
                    ]

    @ormcache("code")
    def search_partner(self, code):
        if not code:
            return False
        partner = (
            self.env["res.partner"]
            .with_context(active_test=False)
            .search([("unilever_ref", "=", code)], limit=1)
        )
        if not partner and not self.ignore_unknown_partner:
            raise ValidationError(_("Partner with code {} missed").format(code))
        return partner.id

    @ormcache("code")
    def search_unilever_category(self, code):
        if not code:
            return False
        category = (
            self.env["edi.unilever.category"]
            .with_context(active_test=False)
            .search([("code", "=", code)], limit=1)
        )
        if not category:
            raise ValidationError(_("Category with code {} missed").format(code))
        return category.id

    @ormcache("code")
    def search_unilever_high_competency(self, code):
        if not code:
            return False
        rec = (
            self.env["edi.unilever.competency"]
            .with_context(active_test=False)
            .search([("code", "=", code)], limit=1)
        )
        if not rec:
            raise ValidationError(_("High competency with code {} missed").format(code))
        return rec.id

    @ormcache("code")
    def search_pricelist(self, code):
        if not code:
            return False
        return (
            self.env["product.pricelist"]
            .search([("name", "=", f"Gescon descuentos {code}")])
            .id
        )

    @ormcache("name")
    def search_agreement(self, name):
        if not name:
            return False
        return self.env["agreement"].search([("name", "=", name)]).id

    def get_pricelist(self, code):
        if not code:
            return False
        pricelist_id = self.search_pricelist(code)
        if not pricelist_id:
            pricelist_id = (
                self.env["product.pricelist"]
                .create({"name": f"Gescon descuentos {code}", "sequence": 1000})
                .id
            )
        return pricelist_id

    def format_date(self, date):
        return fields.Date.to_string(datetime.fromordinal(693594 + int(date)))

    def _prepare_agreement(self, xl_sheet, row_idx):
        partner_id = self.search_partner(int(xl_sheet.cell(row_idx, 0).value))
        code = int(xl_sheet.cell(row_idx, 8).value)
        vals = {
            "name": f"Acuerdo descuento {code}",
            "partner_id": partner_id,
            "dto_type": xl_sheet.cell(row_idx, 1).value,
            "start_date": self.format_date(xl_sheet.cell(row_idx, 5).value),
            "end_date": self.format_date(xl_sheet.cell(row_idx, 6).value),
            "note": code,
            "code": code,
        }
        if vals["dto_type"] in ("G", "P", "S"):
            vals["agreement_type"] = "DTO"
        elif vals["dto_type"] == "R":
            vals["agreement_type"] = "COL"
        elif vals["dto_type"] == "T":
            vals["agreement_type"] = "POL"

        if vals["dto_type"] == "P":
            vals.update(
                {
                    "product_id": self.search_product(
                        int(xl_sheet.cell(row_idx, 2).value)
                    ),
                }
            )
        elif vals["dto_type"] == "G":
            vals.update(
                {
                    "product_group_id": self.search_category(
                        int(xl_sheet.cell(row_idx, 2).value)
                    ),
                }
            )
        elif vals["dto_type"] == "S":
            vals.update(
                {
                    "product_subgroup_id": self.search_category(
                        int(xl_sheet.cell(row_idx, 2).value)
                    ),
                }
            )
        elif vals["dto_type"] == "T":
            # TODO: Terminar
            condition_code = int(xl_sheet.cell(row_idx, 2).value)
            condition_id = self.search_agreement_condition(condition_code, "POL")
            if condition_id:
                vals.update({"agreement_condition_id": condition_id})
        elif vals["dto_type"] == "R":
            value = str(int(xl_sheet.cell(row_idx, 2).value))
            vals.update(
                {
                    "unilever_rappel_group": value[0:-3],
                    "unilever_rappel_subgroup": value[-3:],
                }
            )
        discount = xl_sheet.cell(row_idx, 3).value
        if discount:
            vals.update({"invoice_discount": discount})
        fixed_price = xl_sheet.cell(row_idx, 4).value
        if fixed_price:
            vals["agreement_price"] = fixed_price
        return vals

    def _import_discounts(self, xl_sheet):
        Agreement = self.env["agreement"]
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            vals = self._prepare_agreement(xl_sheet, row_idx)
            if vals.get("partner_id", False):
                agreement_id = self.search_agreement(vals["name"])
                if agreement_id:
                    Agreement.browse(agreement_id).write(vals)
                else:
                    Agreement.create(vals)

    @ormcache("camara", "zona")
    def _get_location_id(self, camara, zona):
        if camara == 20:
            if zona in (1, 2):
                # Helado y congelado
                return self.env.ref("__export__.stock_location_2231_b489da6a").id
            elif zona in (20, 22):
                # Refrigerado y embutido
                return self.env.ref("__export__.stock_location_2232_0c330469").id
            elif zona == 21:
                # Seco
                return self.env.ref("__export__.stock_location_2233_4be3f4fb").id
            elif zona == 23:
                # Publicidad
                return self.env.ref("__export__.stock_location_2230_5df56b21").id
            else:
                return False
        else:
            if zona in (1, 2):
                # Helado y congelado
                return self.env.ref("__export__.stock_location_2225_2b181c95").id
            elif zona in (20, 22):
                # Refrigerado y embutido
                return self.env.ref("__export__.stock_location_2226_9bff2ef9").id
            elif zona == 21:
                # Seco
                return self.env.ref("__export__.stock_location_2227_b11128e2").id
            elif zona == 23:
                # Publicidad
                return self.env.ref("__export__.stock_location_2229_31151418").id
            else:
                return False

    def _import_inventory(self, xl_sheet):
        stock_location_sc_id = 2220
        stock_location_wh_id = 12
        lines_list_sc = []
        lines_list_wh = []
        StockProductionLot = self.env["stock.production.lot"]
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            product = self.env["product.product"].browse(
                self.search_product(int(xl_sheet.cell(row_idx, 1).value))
            )
            if product:
                camara = int(xl_sheet.cell(row_idx, 0).value)
                if camara not in (0, 20):
                    continue
                zona = int(xl_sheet.cell(row_idx, 7).value)
                product.standard_price = xl_sheet.cell(row_idx, 6).value
                qty_base = xl_sheet.cell(row_idx, 4).value
                qty_composicion = xl_sheet.cell(row_idx, 5).value
                qty = qty_base or qty_composicion
                lot_name = xl_sheet.cell(row_idx, 2).value
                lot = StockProductionLot.search(
                    [("name", "=", lot_name), ("product_id", "=", product.id)]
                )
                if not lot:
                    lot = StockProductionLot.create(
                        {
                            "product_id": product.id,
                            "name": lot_name,
                            "expiration_date": self.format_date(
                                xl_sheet.cell(row_idx, 3).value
                            ),
                        }
                    )
                if qty:
                    if camara == 20:
                        lines_list_sc.append(
                            (
                                0,
                                0,
                                {
                                    "product_id": product.id,
                                    "product_uom_id": product.uom_id.id,
                                    "product_qty": qty,
                                    "location_id": self._get_location_id(camara, zona),
                                    "lot_id": lot.id,
                                },
                            )
                        )
                    elif camara == 0:
                        lines_list_wh.append(
                            (
                                0,
                                0,
                                {
                                    "product_id": product.id,
                                    "product_uom_id": product.uom_id.id,
                                    "product_qty": qty,
                                    "location_id": self._get_location_id(camara, zona),
                                    "lot_id": lot.id,
                                },
                            )
                        )
        self.env["stock.move"].create(
            {
                "name": "Gescon inventory Sant Carles",
                "line_ids": lines_list_sc,
                "location_id": stock_location_sc_id,
                "is_inventory": True,
            }
        )
        self.env["stock.move"].create(
            {
                "name": "Gescon inventory Central",
                "line_ids": lines_list_wh,
                "location_id": stock_location_wh_id,
                "is_inventory": True,
            }
        )

    @ormcache("code", "condition_type")
    def search_agreement_condition(self, code, condition_type):
        if not code:
            return False
        return (
            self.env["edi.unilever.agreement.condition"]
            .search([("code", "=", code), ("condition_type", "=", condition_type)])
            .id
        )

    def _prepare_gira_condition(self, xl_sheet, row_idx):
        return {
            "condition_type": "GIRA",
            "name": xl_sheet.cell(row_idx, 1).value,
            "code": int(xl_sheet.cell(row_idx, 0).value),
            "start_date": self.format_date(xl_sheet.cell(row_idx, 2).value),
            "end_date": self.format_date(xl_sheet.cell(row_idx, 3).value),
        }

    def _prepare_pol_condition(self, xl_sheet, row_idx):
        return {
            "condition_type": "POL",
            "name": xl_sheet.cell(row_idx, 1).value,
            "code": int(xl_sheet.cell(row_idx, 0).value),
        }

    def _prepare_gira_condition_line(self, xl_sheet, row_idx):
        code = int(xl_sheet.cell(row_idx, 0).value)
        condition_id = self.search_agreement_condition(code, "GIRA")
        return {
            "agreement_condition_id": condition_id,
            "product_id": self.search_product(int(xl_sheet.cell(row_idx, 1).value)),
            "condition_price": xl_sheet.cell(row_idx, 2).value,
            "condition_discount": xl_sheet.cell(row_idx, 3).value,
        }

    def _prepare_pol_condition_line(self, xl_sheet, row_idx, product_id):
        code = int(xl_sheet.cell(row_idx, 0).value)
        condition_id = self.search_agreement_condition(code, "POL")
        return {
            "agreement_condition_id": condition_id,
            "product_id": product_id,
        }

    def _prepare_agreement_gira(self, xl_sheet, row_idx):
        partner_code = int(xl_sheet.cell(row_idx, 2).value)
        partner_id = self.search_partner(partner_code)
        code = int(xl_sheet.cell(row_idx, 1).value)
        condition_id = self.search_agreement_condition(code, "GIRA")
        condition = self.env["edi.unilever.agreement.condition"].browse(condition_id)
        vals = {
            "name": "Acuerdo GIRA {}-{}-{}".format(
                xl_sheet.cell(row_idx, 0).value, code, partner_code
            ),
            "partner_id": partner_id,
            "agreement_type": "GIRA",
            "dto_type": "GIRA",
            "agreement_condition_id": condition_id,
            "start_date": condition.start_date,
            "end_date": condition.end_date,
        }
        return vals

    def _import_gira(self, xl_workbook):
        # Sheet Agreements Conditions
        xl_sheet = xl_workbook.sheet_by_index(1)
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            self.env["edi.unilever.agreement.condition"].create(
                self._prepare_gira_condition(xl_sheet, row_idx)
            )
        # Sheet Condition Lines
        xl_sheet = xl_workbook.sheet_by_index(0)
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            self.env["edi.unilever.agreement.condition.line"].create(
                self._prepare_gira_condition_line(xl_sheet, row_idx)
            )
        # Sheet Agreements
        xl_sheet = xl_workbook.sheet_by_index(2)
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            vals = self._prepare_agreement_gira(xl_sheet, row_idx)
            if vals.get("partner_id", False):
                self.env["agreement"].create(vals)

    def _import_grupos_turismo(self, xl_workbook):
        # Sheet Grupos
        xl_sheet = xl_workbook.sheet_by_index(1)
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            self.env["edi.unilever.agreement.condition"].create(
                self._prepare_pol_condition(xl_sheet, row_idx)
            )
        # Sheet grupos Lines
        xl_sheet = xl_workbook.sheet_by_index(2)
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            product_id = self.search_product(int(xl_sheet.cell(row_idx, 1).value))
            if product_id:
                self.env["edi.unilever.agreement.condition.line"].create(
                    self._prepare_pol_condition_line(xl_sheet, row_idx, product_id)
                )

    def _relational_product_field(self, table_name, relational_tale):
        sql = """
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s AND ccu.table_name = %s AND
                    ccu.column_name = 'id'
        """
        self.env.cr.execute(sql, (table_name, relational_tale))
        records = self.env.cr.fetchall()
        if not records:
            return []
        return records[:1][0][1]

    def _change_foreign_key_refs(
        self,
        model_name,
        template_ids,
        record_ids,
        origin_record_id,
        target_record_id,
        exclude_columns,
    ):
        # As found on https://stackoverflow.com/questions/1152260
        # /postgres-sql-to-list-table-foreign-keys
        self.env.cr.execute(
            """ SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE constraint_type = 'FOREIGN KEY'
                AND ccu.table_name = %s and ccu.column_name = 'id'
            """,
            (self.env[model_name]._table,),
        )
        for table, column in self.env.cr.fetchall():
            if (table, column) in exclude_columns:
                continue

            filter_raltional_table = "product_product"
            product_relation_field = self._relational_product_field(
                table, "product_product"
            )
            if not product_relation_field:
                product_relation_field = self._relational_product_field(
                    table, "product_template"
                )
                filter_raltional_table = "product_template"
            if table == "product_template":
                product_relation_field = "id"
            if not product_relation_field:
                continue

            with self.env.cr.savepoint():
                sql = """
                    UPDATE %(table)s
                    SET %(column)s = %(target_record_id)s
                    WHERE %(column)s = %(origin_record)s AND
                        %(column_filter)s in %(record_ids)s
                    """
                args = {
                    "table": AsIs(table),
                    "column": AsIs(column),
                    "origin_record": origin_record_id,
                    "column_filter": AsIs(product_relation_field),
                    "record_ids": tuple(record_ids),
                    "target_record_id": target_record_id,
                }
                if filter_raltional_table in ("product_template", "id"):
                    args["record_ids"] = tuple(template_ids)
                logged_query(self.env.cr, sql, args, skip_no_result=True)

    def change_uom(self, xl_workbook):
        xl_sheet = xl_workbook.sheet_by_index(0)
        Product = self.env["product.product"]
        for row_idx in range(1, xl_sheet.nrows):
            code = str(xl_sheet.cell(row_idx, 1).value).split(".")[0]
            product = Product.browse(self.search_product(code, add_vir=False))
            if not product:
                raise UserError(_(f"Producto {code} no encontrado"))
            old_uom_id = self.search_uom(xl_sheet.cell(row_idx, 2).value)
            new_uom_id = self.search_uom(xl_sheet.cell(row_idx, 3).value)
            self._change_foreign_key_refs(
                "uom.uom",
                product.product_tmpl_id.ids,
                product.ids,
                old_uom_id,
                new_uom_id,
                [],
            )

    def _update_vendor_product_code(self, xl_workbook):
        # https://www.tecnativa.com/web#id=18107&view_type=form&
        # model=project.task
        xl_sheet = xl_workbook.sheet_by_index(0)
        Product = self.env["product.product"]
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            unilever_ref = str(int(xl_sheet.cell(row_idx, 0).value))
            product_code = xl_sheet.cell(row_idx, 2).value
            is_product_unilever = xl_sheet.cell(row_idx, 1).value == 533.00
            product_name = xl_sheet.cell(row_idx, 3).value
            seller_id = 42803
            if not is_product_unilever:
                continue
            product = Product.search([("unilever_ref", "=", unilever_ref)])
            if not product:
                continue
            unilever_seller = product.product_tmpl_id.seller_ids.filtered(
                lambda x, si=seller_id: x.name.id == si
            )
            if not unilever_seller:
                unilever_seller.create(
                    {
                        "name": seller_id,
                        "product_tmpl_id": product.product_tmpl_id.id,
                        "product_name": product_name,
                        "product_code": product_code,
                    }
                )
            else:
                if unilever_seller.product_code != product_code:
                    unilever_seller.product_code = product_code

    def _update_unilever_participation(self, xl_workbook):
        # https://www.tecnativa.com/web#id=18086&view_type=form&
        # model=project.task
        xl_sheet = xl_workbook.sheet_by_index(0)
        EdiUnileverAgreement = self.env["agreement"]
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            customer = str(int(xl_sheet.cell(row_idx, 0).value))
            grupo = int(xl_sheet.cell(row_idx, 2).value)
            participation = xl_sheet.cell(row_idx, 5).value
            sub_grupo = int(xl_sheet.cell(row_idx, 6).value)
            vals = {"unilever_participation_percent": participation}
            partners = self.env["res.partner"].search([("unilever_ref", "=", customer)])
            if not partners:
                continue
            agreements = EdiUnileverAgreement.search(
                [
                    ("partner_id", "in", partners.ids),
                    ("agreement_type", "in", ("COL", "GIRA")),
                    "|",
                    ("unilever_rappel_subgroup", "!=", False),
                    ("unilever_rappel_group", "!=", False),
                ]
            )
            if not agreements:
                continue
            filter_agreements = agreements.filtered(
                lambda x, sg=sub_grupo: int(x.unilever_rappel_subgroup) == sg
            )
            if filter_agreements:
                filter_agreements.write(vals)
                continue
            filter_agreements = agreements.filtered(
                lambda x, g=grupo: (int(x.unilever_rappel_group) == g)
            )
            if filter_agreements:
                filter_agreements.write(vals)
                continue

    def _archive_virginia_partners(self, xl_workbook):
        # https://www.tecnativa.com/web#id=18529&view_type=form&
        # model=project.task
        xl_sheet = xl_workbook.sheet_by_index(0)
        ResPartner = self.env["res.partner"]
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            cli_fbaj = int(xl_sheet.cell(row_idx, 14).value)
            if cli_fbaj == 0:
                continue
            partner_code = int(xl_sheet.cell(row_idx, 1).value)
            partner_id = self.search_partner(partner_code)
            if not partner_id:
                continue
            partners = ResPartner.search([("id", "child_of", partner_id)])
            if not partners:
                continue
            vals = {}
            for partner in partners:
                vals = {
                    "active": False,
                    "comment": "{}\nArchivado: {} - {}".format(
                        partner.comment, "cli_fbaj", cli_fbaj
                    ),
                }
                body = "Partner archived with date: %s" % cli_fbaj
                partner.message_post(body=body)
            partners.write(vals)

    @ormcache("name")
    def get_category_medios(self, name):
        if not name:
            return False
        category = self.env["product.category"].search([("name", "=", name)])
        if not category:
            category = self.env["product.category"].create(
                {
                    "name": name,
                    "parent_id": (
                        self.get_category_medios("Medios de frío")
                        if name != "Medios de frío"
                        else False
                    ),
                }
            )
        return category.id

    def format_date_str(self, date):
        if not date:
            return False
        return fields.Date.to_string(datetime.strptime(date, "%d/%m/%Y"))

    @ormcache("partner_id")
    def _get_group_id(self, partner_id):
        key = "unilever_fresh_asset_%s" % partner_id
        ProcurementGroup = self.env["procurement.group"]
        group = ProcurementGroup.search([("name", "=", key)])
        if not group:
            group = ProcurementGroup.create({"name": key, "partner_id": partner_id})
        return group.id

    def _import_medios(self, xl_workbook):
        # https://www.tecnativa.com/web#id=18671&view_type=form
        # &model=project.task
        location_vendor_id = 8
        location_customer_id = 9
        location_stock_id = 12  # WH/Stock Reus
        in_picking_type_id = 1
        out_picking_type_id = 2
        xl_sheet = xl_workbook.sheet_by_index(0)
        odoo_partner_sheet = xl_workbook.sheet_by_index(1)
        odoo_partners = {}
        for row_idx in range(1, odoo_partner_sheet.nrows):
            if odoo_partner_sheet.cell(row_idx, 7).value:
                cod_partner = int(odoo_partner_sheet.cell(row_idx, 0).value)
                odoo_ext_ref = odoo_partner_sheet.cell(row_idx, 7).value
                odoo_partners[cod_partner] = self.env.ref(odoo_ext_ref)
            else:
                pass
        # ResPartner = self.env['res.partner']
        # ProductCategory = self.env['product.category']
        StockProductionLot = self.env["stock.production.lot"]
        # StockPicking = self.env['stock.picking']
        StockMove = self.env["stock.move"]
        # if str(xl_sheet.cell(0, 9).value) == 'Contrato':
        #     col_lot = 2
        #     col_tipo = 3
        #     col_modelo = 4
        #     col_fecha_lectura = 6
        #     col_fecha_control = 7
        #     col_fecha_movimiento = 8
        #     col_contrato = 9
        #     col_valor = 10
        #     col_partner = 12
        # else:
        #     col_lot = 1
        #     col_tipo = 99
        #     col_modelo = 4
        #     col_fecha_lectura = 99
        #     col_fecha_control = 99
        #     col_fecha_movimiento = 0
        #     col_contrato = 99
        #     col_valor = 99
        #     col_partner = 99
        new_moves = StockMove.browse()
        missed_partner_list = []
        for row_idx in range(1, xl_sheet.nrows):  # Iterate through rows
            lot_name = str(xl_sheet.cell(row_idx, 2).value).replace(".0", "")
            tipo_nevera = xl_sheet.cell(row_idx, 3).value
            modelo = xl_sheet.cell(row_idx, 4).value
            fecha_lectura = self.format_date_str(xl_sheet.cell(row_idx, 6).value)
            fecha_control = self.format_date_str(xl_sheet.cell(row_idx, 7).value)
            fecha_movimiento = self.format_date_str(xl_sheet.cell(row_idx, 8).value)
            contrato = (
                int(xl_sheet.cell(row_idx, 9).value)
                if xl_sheet.cell(row_idx, 9).value
                else False
            )
            valor = xl_sheet.cell(row_idx, 10).value
            partner_code = (
                int(xl_sheet.cell(row_idx, 12).value)
                if xl_sheet.cell(row_idx, 12).value
                else False
            )
            product_id = self.search_product_by_name(modelo)
            if not product_id:
                product_id = (
                    self.env["product.product"]
                    .create(
                        {
                            "name": modelo,
                            "categ_id": self.get_category_medios(tipo_nevera),
                            "sale_ok": False,
                            "purchase_ok": False,
                            "tracking": "serial",
                            "type": "product",
                            "standard_price": valor,
                        }
                    )
                    .id
                )
            product = self.env["product.product"].browse(product_id)
            lot = StockProductionLot.search(
                [("name", "=", lot_name), ("product_id", "=", product_id)]
            )
            if not lot:
                lot = StockProductionLot.create(
                    {
                        "product_id": product_id,
                        "name": lot_name,
                        "use_date": fecha_lectura,
                        "expiration_date": fecha_control,
                    }
                )
            partner_id = self.search_partner(partner_code)
            if partner_code and not partner_id:
                if partner_code in odoo_partners:
                    partner_id = odoo_partners[partner_code].id
                else:
                    missed_partner_list.append(partner_code)
            group_id = self._get_group_id(partner_id)
            move_vals = {
                "name": product.name,
                "partner_id": partner_id,
                "product_id": product_id,
                "location_id": location_vendor_id,
                "location_dest_id": (
                    location_customer_id if partner_code else location_stock_id
                ),
                "product_uom": product.uom_id.id,
                "product_uom_qty": 1.0,
                "origin": "UnileverFreshAsset",
                "note": contrato,
                "group_id": group_id,
                "picking_type_id": (
                    out_picking_type_id if partner_code else in_picking_type_id
                ),
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "location_id": location_vendor_id,
                            "location_dest_id": (
                                location_customer_id
                                if partner_code
                                else location_stock_id
                            ),
                            "product_id": product_id,
                            "product_uom_id": product.uom_id.id,
                            "qty_done": 1.0,
                            "lot_id": lot.id,
                            "lot_name": lot.name,
                        },
                    )
                ],
            }
            if fecha_movimiento:
                move_vals.update(
                    {
                        "create_date": fecha_movimiento,
                        "date": fecha_movimiento,
                        "date_expected": fecha_movimiento,
                    }
                )
                move_vals["move_line_ids"][0][2].update({"date": fecha_movimiento})
            new_moves |= StockMove.with_context(
                tracking_disable=True,
                mail_notrack=True,
                mail_create_nolog=True,
            ).create(move_vals)
        missed_partner_list = list(set(missed_partner_list))
        if missed_partner_list:
            _logger.info("Codigos de cliente no encontrados:\n%s" % missed_partner_list)
        new_moves.with_context(
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nolog=True,
        )._action_done()
        self.env.cr.execute(
            """
            UPDATE stock_move SET date = date_expected WHERE id in %s
        """,
            (new_moves._ids,),
        )
        self.env.cr.execute(
            """
            UPDATE stock_move_line sml SET picking_id = (SELECT picking_id FROM
                stock_move sm WHERE sm.id=sml.move_id)
            WHERE move_id in %s
        """,
            (new_moves._ids,),
        )

    def _unilever_partner_update(self, xl_workbook):
        xl_sheet = xl_workbook.sheet_by_index(0)
        ResPartner = self.env["res.partner"]
        for row_idx in range(1, xl_sheet.nrows):
            partner_code = int(xl_sheet.cell(row_idx, 0).value)
            category_code = int(xl_sheet.cell(row_idx, 10).value)
            competencia_alta = xl_sheet.cell(row_idx, 11).value
            unilever_local_code = int(xl_sheet.cell(row_idx, 15).value)
            unilever_dealer_chain = int(xl_sheet.cell(row_idx, 16).value)
            partner_id = self.search_partner(partner_code)
            if not partner_id:
                continue
            partner = ResPartner.browse(partner_id)
            unilever_category_id = self.search_unilever_category(category_code)
            unilever_high_competency_id = self.search_unilever_high_competency(
                competencia_alta
            )
            vals = {
                "unilever_category_id": unilever_category_id,
                "unilever_high_competency_id": unilever_high_competency_id,
                "unilever_local_code": unilever_local_code,
                "unilever_dealer_chain": unilever_dealer_chain,
            }
            partner.write(vals)

    def _update_pol_price(self, xl_workbook):
        # agreements = self.env['agreement'].search([
        #     ('agreement_type', '=', 'POL'),
        # ])
        # for agreement in agreements:
        #     if not agreement.agreement_condition_id:
        #         continue
        #     match = re.search(r'([0-9]*,[0-9]{2})\€',
        #                      agreement.agreement_condition_id.name)
        #     if match:
        #         agreement.guaranteed_price = float(
        #             match.group(1).replace(',', '.'))
        xl_sheet = xl_workbook.sheet_by_index(0)
        agree_code = False
        for row_idx in range(1, xl_sheet.nrows):
            if agree_code == xl_sheet.cell(row_idx, 1).value[:2]:
                continue
            agree_code = xl_sheet.cell(row_idx, 1).value[:2]
            guaranteed_price = float(xl_sheet.cell(row_idx, 3).value)
            agreements = self.env["agreement"].search(
                [
                    ("agreement_type", "=", "POL"),
                    ("agreement_condition_id.code", "=", agree_code),
                ]
            )
            for agreement in agreements:
                agreement.guaranteed_price = guaranteed_price

    def _unilever_partner_sync(self, xl_workbook):
        xl_sheet = xl_workbook.sheet_by_index(0)
        ResPartner = self.env["res.partner"]
        ResPartner.search([("unilever_ref", "!=", False)]).with_context(
            skip_update_unilever_check=True
        ).write({"unilever_move_type": "A"})
        ResPartner.search(
            [("unilever_ref", "!=", False), ("active", "=", False)]
        ).with_context(skip_update_unilever_check=True).write(
            {"unilever_move_type": "B"}
        )
        existing_partners = []
        missing_partners = []
        for row_idx in range(1, xl_sheet.nrows):
            unilever_partner_code = int(xl_sheet.cell(row_idx, 1).value)
            unilever_dealer_chain = xl_sheet.cell(row_idx, 4).value
            unilever_local_code = xl_sheet.cell(row_idx, 5).value
            partner = ResPartner.search(
                [("unilever_ref", "=", unilever_partner_code)], limit=1
            )
            if not partner:
                missing_partners.append(unilever_partner_code)
                continue
            existing_partners.append(partner.id)
            vals = {
                "unilever_move_type": "M",
                "unilever_dealer_chain": unilever_dealer_chain or False,
                "unilever_local_code": unilever_local_code or False,
            }
            partner.with_context(skip_update_unilever_check=True).write(vals)
        _logger.info(f"Missing partners: {missing_partners}")
        _logger.info(f"Existing partners: {existing_partners}")

    @ormcache("code")
    def search_unilever_rappel_group(self, code):
        if not code:
            return False
        group = self.env["unilever.rappel.group"].search([("code", "=", code)], limit=1)
        # if not group:
        #     raise ValidationError(
        #         'Rappel group with code {} missed'.format(code))
        return group.id

    @ormcache("unilever_ref")
    def search_unilever_rappel_group_by_ref(self, unilever_ref):
        if not unilever_ref:
            return False
        group = self.env["unilever.rappel.group"].search(
            [("unilever_ref", "=", unilever_ref)], limit=1
        )
        return group.id

    def _prepare_agreement_dto_rappel(
        self, xl_sheet, row_idx, rappel_group_forced=False, index_group=False
    ):
        if xl_sheet.name == "dto-rappel-directo":
            type_dto = "Direct"
        elif xl_sheet.name == "dto-rappel-directo-descuento-factura":
            type_dto = "Direct dto invoice"
        else:
            type_dto = "Grouped"

        partner_id = self.search_partner(int(xl_sheet.cell(row_idx, 0).value))
        code = int(xl_sheet.cell(row_idx, 45).value)
        invoice_discount = float(xl_sheet.cell(row_idx, 7).value)
        if not rappel_group_forced:
            group = int(xl_sheet.cell(row_idx, 2).value)
            sub_group = int(xl_sheet.cell(row_idx, 6).value)
        rappel_group = rappel_group_forced or sub_group or group
        cadena = True if str(xl_sheet.cell(row_idx, 4).value) == "S" else False
        grouped_group = True if str(xl_sheet.cell(row_idx, 16).value) == "S" else False
        grouped_subgroup = (
            True if str(xl_sheet.cell(row_idx, 17).value) == "S" else False
        )
        contribucion = xl_sheet.cell(row_idx, 5).value
        # Calcular escalado del rappel
        escalado_index_start = 20
        last_qty = 0.00
        escalado = []
        for _i in range(10):
            qty = xl_sheet.cell(row_idx, escalado_index_start).value
            if qty == 0.0:
                continue
            percent_dto = xl_sheet.cell(row_idx, escalado_index_start + 1).value
            escalado.append(f"{last_qty:.2f}-{qty:.2f}:{percent_dto:.2f}")
            last_qty = xl_sheet.cell(row_idx, escalado_index_start).value
            escalado_index_start += 2
        anual_discount_percent = ";".join(escalado)
        vals = {
            "name": f"Acuerdo descuento rappel {type_dto} {code}",
            "partner_id": partner_id,
            "agreement_type": "DTO",
            "start_date": "2018-01-01",
            # 'start_date': self.format_date(xl_sheet.cell(row_idx, 43).value),
            # 'end_date': self.format_date(xl_sheet.cell(row_idx, 6).value),
            "note": code,
            "code": f"{type_dto}-dto-{code}",
            "chain": cadena,
            "grouped_group": grouped_group,
            "grouped_subgroup": grouped_subgroup,
            "unilever_rappel_group_id": self.search_unilever_rappel_group(rappel_group),
            "unilever_participation_percent": contribucion,
            "move_type": "M",
            "invoice_discount": invoice_discount,
            "year": 2019,
        }
        if anual_discount_percent:
            vals["anual_discount_percent"] = anual_discount_percent
        if index_group:
            vals["name"] = "{}-{}".format(vals["name"], index_group)
        return vals

    def _create_agreement_dto(
        self,
        xl_sheet,
        row_idx,
        missing_partners=None,
        rappel_group=False,
        index_group=False,
    ):
        if missing_partners is None:
            missing_partners = []
        Agreement = self.env["agreement"]
        vals = self._prepare_agreement_dto_rappel(
            xl_sheet, row_idx, rappel_group_forced=rappel_group, index_group=index_group
        )
        if vals.get("partner_id", False):
            agreements = self.env["agreement"].search([("name", "=", vals["name"])])
            if agreements:
                agreements.write(vals)
            else:
                Agreement.create(vals)
        else:
            missing_partners.append(int(xl_sheet.cell(row_idx, 0).value))

    def _import_dto_rappel(self, xl_workbook):
        xl_sheet = xl_workbook.sheet_by_name("dto-rappel-directo")
        missing_partners = []
        for row_idx in range(1, xl_sheet.nrows):
            self._create_agreement_dto(
                xl_sheet, row_idx, missing_partners=missing_partners
            )
        _logger.info(f"Direct Partner not found: {list(set(missing_partners))}")
        xl_sheet = xl_workbook.sheet_by_name("clientes con grupo rappel 100")
        group_exploit = [108, 109, 110, 111]
        missing_partners = []
        for row_idx in range(1, xl_sheet.nrows):
            for group in group_exploit:
                self._create_agreement_dto(
                    xl_sheet,
                    row_idx,
                    missing_partners=missing_partners,
                    rappel_group=group,
                    index_group=group,
                )
        _logger.info(f"Grouped Partner not found: {list(set(missing_partners))}")
        # Last import agreements with invoice discount
        xl_sheet = xl_workbook.sheet_by_name("dto-rappel-directo-descuento-factura")
        missing_partners = []
        for row_idx in range(1, xl_sheet.nrows):
            invoice_discount = float(xl_sheet.cell(row_idx, 7).value)
            if not invoice_discount:
                continue
            self._create_agreement_dto(
                xl_sheet, row_idx, missing_partners=missing_partners
            )
        _logger.info(f"Direct Partner not found: {list(set(missing_partners))}")

    def search_lot(self, name):
        StockProductionLot = self.env["stock.production.lot"]
        lot = StockProductionLot.with_context(active_test=False).search(
            [("name", "=", name)]
        )
        return lot

    def _import_agreement_mef(self, xl_workbook):
        xl_sheet = xl_workbook.sheet_by_name("Listados")
        Agreement = self.env["agreement"]
        Picking = self.env["stock.picking"]
        agreement_type_mef = self.env.ref("agreement_unilever_mef.agreement_type_mef")
        contacto_unilever = self.env["res.partner"].search(
            [("name", "=", "Carlos Ribó")], limit=1
        )

        missing_partners = []
        missing_lot = []
        missing_pikcing = []
        for row_idx in range(1, xl_sheet.nrows):
            cliente = xl_sheet.cell(row_idx, 12).value
            contrato = xl_sheet.cell(row_idx, 9).value
            matricula = xl_sheet.cell(row_idx, 2).value
            ubicacion = xl_sheet.cell(row_idx, 11).value
            fecha = xl_sheet.cell(row_idx, 8).value
            valor = xl_sheet.cell(row_idx, 10).value
            if ubicacion == "Almacén":
                continue
            if not contrato:
                continue
            if isinstance(contrato, (float, int)):  # noqa UP38
                contrato = str(int(contrato))
            if isinstance(matricula, (float, int)):  # noqa UP38
                matricula = str(int(matricula))
            _logger.info(f"Importando contrato: {contrato} de {row_idx}")
            partner_id = self.search_partner(int(cliente))
            if not partner_id:
                missing_partners.append(int(cliente))
                continue
            lot = self.search_lot(matricula)
            if not lot:
                missing_lot.append(matricula)
                continue
            picking = Picking.browse()
            last_move_line = lot.last_move_line_id
            if last_move_line.location_dest_id.usage == "customer":
                picking = last_move_line.picking_id
            if not last_move_line or not picking:
                missing_pikcing.append(matricula)
            date = datetime.strptime(fecha, "%d/%m/%Y").date()
            agreement = Agreement.with_context(active_test=False).search(
                [("domain", "=", "unilever_mef"), ("code", "=", contrato)]
            )
            vals = {
                "name": f"Acuerdo MEF {contrato}",
                "partner_id": partner_id,
                "code": contrato,
                "agreement_type_id": agreement_type_mef.id,
                "domain": "unilever_mef",
                "mef_lot_id": lot.id,
                "mef_picking_id": picking.id,
                "mef_product_standard_price": round(float(valor), 2),
                "mef_supplier_contact_id": contacto_unilever.id,
                "signature_date": date,
                "start_date": date,
            }
            if agreement:
                agreement.write(vals)
            else:
                agreement.create(vals)
        _logger.info(f"Partner not found: {list(set(missing_partners))}")
        _logger.info(f"Serial number not found: {list(set(missing_lot))}")
        _logger.info(f"Serial number without move: {list(set(missing_pikcing))}")

    def _import_agreement_consumption(self, xl_workbook):
        xl_sheet = xl_workbook.sheet_by_name("mapeo y consumos")
        Agreement = self.env["agreement"]
        agreements = Agreement.search(
            [
                # ('year', '<', 2020),
                "|",
                ("anual_discount_percent", "!=", False),
                ("rebate_section_ids", "!=", False),
            ],
            order="year",
        )

        for row_idx in range(1, xl_sheet.nrows):
            consumption = xl_sheet.cell(row_idx, 8).value
            if not consumption:
                continue
            partner = self.env.ref(xl_sheet.cell(row_idx, 3).value, False)
            excel_group = xl_sheet.cell(row_idx, 4).value
            rappel_group_id = self.search_unilever_rappel_group_by_ref(excel_group)
            if not partner or not rappel_group_id:
                # print("Not info at row {} Partner: {} Group: {} Consumo {}".format(
                _logger.info(
                    "Not info at row {} Partner: {} Group: {} Consumption {}".format(
                        row_idx,
                        partner and (partner.id, partner.name) or "",
                        excel_group,
                        consumption,
                    )
                )
                continue
            agreement = agreements.filtered(
                lambda a, p=partner, rgi=rappel_group_id: a.partner_id == p
                and a.unilever_rappel_group_id.id == rgi
            )[:1]
            if agreement:
                agreement.additional_consumption = consumption
                _logger.info(
                    "Agreement {} updated with {}".format(
                        (agreement.id, agreement.name),
                        consumption,
                    )
                )
            else:
                # print("Agreement not found at row {}: {} Group: {}".format(
                _logger.info(
                    "Agreement not found at row {}: {} Group: {}".format(
                        row_idx + 1,
                        partner.name,
                        excel_group,
                    )
                )

    def _refund_unilever_mef(self, xl_workbook):
        StockMove = self.env["stock.move"]
        StockMoveLine = self.env["stock.move.line"]
        StockLocation = self.env["stock.location"]
        StockProductionLot = self.env["stock.production.lot"]

        xl_sheet = xl_workbook.sheet_by_index(0)
        lots_to_refund = []
        for row_idx in range(1, xl_sheet.nrows):
            lots = xl_sheet.cell(row_idx, 4).value
            lots_splitted = lots.split(",")
            lots_to_refund.extend([x.strip() for x in lots_splitted])
        _logger.info(f"Lots to refund: {lots_to_refund}")
        production_lots = StockProductionLot.search([("name", "in", lots_to_refund)])
        picking_type = self.env.ref("agreement_unilever_mef.fresh_asset_picking_type")
        location_customer = self.env.ref("stock.stock_location_customers")
        location_stock = StockLocation.browse(2471)  # Medios de frío
        # location_stock = self.env.ref("stock.stock_location_stock")
        procurement = self.env["procurement.group"].create({})
        returned_moves = StockMove.browse()
        picking = (
            self.env["stock.picking"]
            .with_context(
                default_picking_type_id=picking_type.id,
                default_location_id=location_customer.id,
                default_location_dest_id=location_stock.id,
                deafult_group_id=procurement.id,
            )
            .create({"origin": "UnileverFreshAsset Devolución forzada"})
        )
        lots_to_skip = StockProductionLot.browse()
        for lot in production_lots:
            last_move_line = lot.last_move_line_id
            if last_move_line.location_dest_id == location_stock:
                lots_to_skip |= lot
                continue
            _logger.info(f"Process lot: {lot.name} - Product: {lot.product_id.name}")
            move = StockMove.create(
                {
                    "name": f"MEF: Devolución forzada - {lot.product_id.name}",
                    "origin": f"MEF: {last_move_line.picking_id.name}",
                    "picking_type_id": picking_type.id,
                    "location_id": location_customer.id,
                    "location_dest_id": location_stock.id,
                    "product_id": lot.product_id.id,
                    "product_uom_qty": 1.0,
                    "product_uom": lot.product_id.uom_id.id,
                    "picking_id": picking.id,
                }
            )
            returned_moves |= move
        picking.action_confirm()
        for lot in production_lots - lots_to_skip:
            StockMoveLine.create(
                {
                    "picking_id": picking.id,
                    "location_id": location_customer.id,
                    "location_dest_id": location_stock.id,
                    "product_id": lot.product_id.id,
                    "qty_done": 1.0,
                    "product_uom_id": lot.product_id.uom_id.id,
                    "lot_id": lot.id,
                    "lot_name": lot.name,
                    "move_id": picking.move_lines.filtered(
                        lambda m, lo=lot: m.product_id == lo.product_id
                    ).id,
                }
            )
        _logger.info(f"Returned moves: {returned_moves}")

    def _change_unilever_mef_moves_to_E(self, file):
        StockMove = self.env["stock.move"]
        StockQuant = self.env["stock.quant"]
        StockMoveLine = self.env["stock.move.line"]
        StockProductionLot = self.env["stock.production.lot"]
        lots_type_a = []
        for line in io.BytesIO(file).readlines():
            move_type = line[23:24]
            if move_type.decode() == "A":
                lot = line[:13].decode().strip()
                lots_type_a.append(lot)
        quants = StockQuant.search(
            [
                ("lot_id.name", "in", lots_type_a),
                ("product_id.tracking", "=", "serial"),
                ("quantity", ">", 0),
                ("location_id", "=", self.env.ref("stock.stock_location_customers").id),
            ]
        )
        forbidden_lots = quants.mapped("lot_id.name")
        lots_clean = list(set(lots_type_a) - set(forbidden_lots))
        num_lots_to_process = int(len(lots_clean) * 80 / 100)
        lots = StockProductionLot.search(
            [
                ("name", "in", lots_clean[:num_lots_to_process]),
            ]
        )
        picking_type = self.env.ref("agreement_unilever_mef.fresh_asset_picking_type")
        location_customer = self.env.ref("stock.stock_location_customers")
        # location_stock = StockLocation.browse(2471)  # Medios de frío
        location_stock = self.env.ref("stock.stock_location_stock")
        procurement = self.env["procurement.group"].create({})
        picking = (
            self.env["stock.picking"]
            .with_context(
                default_picking_type_id=picking_type.id,
                default_location_id=location_stock.id,
                default_location_dest_id=location_customer.id,
                deafult_group_id=procurement.id,
            )
            .create({"origin": "UnileverFreshAsset 80% A to E"})
        )
        for lot in lots:
            StockMove.create(
                {
                    "name": f"MEF: Cambio 80% A to E - {lot.product_id.name}",
                    "picking_type_id": picking_type.id,
                    "location_id": location_stock.id,
                    "location_dest_id": location_customer.id,
                    "product_id": lot.product_id.id,
                    "product_uom_qty": 1.0,
                    "product_uom": lot.product_id.uom_id.id,
                    "picking_id": picking.id,
                }
            )
        picking.action_confirm()
        for lot in lots:
            StockMoveLine.create(
                {
                    "picking_id": picking.id,
                    "location_id": location_stock.id,
                    "location_dest_id": location_customer.id,
                    "product_id": lot.product_id.id,
                    "qty_done": 1.0,
                    "product_uom_id": lot.product_id.uom_id.id,
                    "lot_id": lot.id,
                    "lot_name": lot.name,
                    "move_id": picking.move_lines.filtered(
                        lambda m, lo=lot: m.product_id == lo.product_id
                    ).id,
                }
            )
        _logger.info(f"Cambio 80% A to E: {picking.name}")
        picking.button_validate()
        # Return the picking manually in UI

    def _unilever_mef_sn_to_scrap(self, xl_sheet):
        StockMoveLine = self.env["stock.move.line"]
        StockProductionLot = self.env["stock.production.lot"]
        StockScrap = self.env["stock.scrap"]
        lot_with_out_moves = StockProductionLot.browse()
        for row_idx in range(1, xl_sheet.nrows):
            lot_name = str(xl_sheet.cell(row_idx, 0).value).replace(".0", "")
            lot = StockProductionLot.search([("name", "=", lot_name)])
            sml = StockMoveLine.search(
                [
                    ("product_id", "=", lot.product_id.id),
                    ("lot_id", "=", lot.id),
                ],
                limit=1,
                order="date DESC, id DESC",
            )
            _logger.info(
                f"Lot {lot_name} moved to scrap from {sml.location_dest_id.name}"
            )
            if sml and not sml.location_dest_id.scrap_location:
                scrap = StockScrap.create(
                    {
                        "company_id": sml.company_id.id,
                        "picking_id": sml.picking_id.id,
                        "product_id": sml.product_id.id,
                        "product_uom_id": sml.product_uom_id.id,
                        "lot_id": sml.lot_id.id,
                        "scrap_qty": 1.0,
                        "location_id": sml.location_dest_id.id,
                    }
                )
                scrap._onchange_product_id()
                scrap.do_scrap()
            else:
                lot_with_out_moves |= lot
        _logger.info("Lot without moves {}".format(lot_with_out_moves.mapped("name")))
        lot_with_out_moves.write({"unilever_low_reason": "D"})

    def _unilever_uncheck_dto_settlements_lines(self, xl_sheet):
        ResPartner = self.env["res.partner"]
        Agreement = self.env["agreement"]
        # Acotar registros implicados
        communication_history = self.env["edi.unilever.communication.history"].search(
            [
                ("file_name", "like", f"%{self.filename[-8:]}"),
                ("edi_backend_id", "=", 14),
            ]
        )
        settlement_lines = communication_history.get_applied_records()
        lines_to_uncheck = self.env["agreement.rebate.settlement.line"].browse()
        for row_idx in range(1, xl_sheet.nrows):
            partner_code = xl_sheet.cell(row_idx, 7).value
            if not partner_code:
                continue
            if partner_code == "4311388":
                partner_code = "4312343"
            if partner_code == "430115":
                partner_code = "5850"
            if partner_code == "98":
                partner_code = "4312078"
            subgrupo_rappel = xl_sheet.cell(row_idx, 9).value
            # ul_contribution_amount = float(xl_sheet.cell(row_idx, 12).value)
            partner = ResPartner.search([("unilever_ref", "=", partner_code)])
            if not partner:
                partner = ResPartner.with_context(active_test=False).search(
                    [("unilever_ref", "=", partner_code)]
                )
            # Cosas raras
            if partner_code == "2912":
                # partner = partner.filtered(lambda p: p.id == 93400)
                partner = partner.filtered(lambda p: p.id == 82451)
            if partner_code == "430055":
                partner = partner.filtered(lambda p: p.id == 89516)
            agreement_domain = [
                ("partner_id", "=", partner.id),
                ("unilever_rappel_group_id.unilever_ref", "=", subgrupo_rappel),
                ("agreement_type", "=", "DTO"),
                "|",
                ("end_date", "=", False),
                ("end_date", ">", "2021-12-31"),
            ]
            agreement = Agreement.search(agreement_domain)
            if not agreement:
                # Search archived
                agreement = Agreement.with_context(active_test=False).search(
                    agreement_domain
                )
            if partner_code == "5003646":
                agreement = Agreement.browse(8047)
            if partner_code == "4312150":
                agreement = Agreement.browse(11833)
            domain = [("unilever_rappel_group_id.unilever_ref", "=", subgrupo_rappel)]
            if not agreement:
                raise ValidationError(
                    _(f"No agreement for partner_code: {partner_code}")
                )
            if len(agreement) > 1:
                _logger.info(f"DOS ACUERDOS IGUALES {agreement}")
                agreement = agreement[:1]
            if agreement[:1].chain:
                child_partners = ResPartner.search(
                    [("unilever_dealer_chain", "=", partner_code)]
                )
                if child_partners:
                    domain.append(("partner_id", "in", child_partners.ids))
                else:
                    child_partners = ResPartner.search(
                        [("unilever_dealer_chain", "=", partner.unilever_dealer_chain)]
                    )
                    if child_partners:
                        domain.append(("partner_id", "in", child_partners.ids))
                    else:
                        domain.append(("partner_id", "=", partner.id))
            else:
                domain.append(("partner_id", "=", partner.id))
            lines = settlement_lines.filtered_domain(domain)
            if lines:
                lines_to_uncheck |= lines
            else:
                raise ValidationError(
                    _(f"No settlements lines for partner_code: {partner_code}")
                )
        if lines_to_uncheck:
            _logger.info(
                "Settlement line to uncheck TOTAL: {} - {}".format(
                    len(lines_to_uncheck), lines_to_uncheck.ids
                )
            )
        # Uncomment to write
        lines_to_uncheck.write({"unilever_state": "not_sent"})
        _logger.info(f"Affected Settlement Lines: {lines_to_uncheck.ids}")

    def _unilever_match_pro_file(self, xl_sheet):
        ProductTemplate = self.env["product.template"]
        products_no_match = []
        for row_idx in range(0, xl_sheet.nrows):
            mrdr_ref = str(xl_sheet.cell(row_idx, 0).value).lstrip("0")
            unilever_ref = str(xl_sheet.cell(row_idx, 2).value).lstrip("0")
            product = ProductTemplate.with_context(active_test=False).search(
                [("unilever_ref", "=", unilever_ref), ("unilever_ref", "!=", False)]
            )
            if product:
                product.unilever_mrdr_ref = mrdr_ref
                _logger.info(
                    f"Product unilever_ref: {unilever_ref} updated MRDR: {mrdr_ref}"
                )
            else:
                product = ProductTemplate.with_context(active_test=False).search(
                    [("unilever_ref", "=", mrdr_ref), ("unilever_ref", "!=", False)]
                )
                if product:
                    product.unilever_mrdr_ref = mrdr_ref
                    _logger.info(
                        f"Product unilever_ref: {unilever_ref} updated MRDR: {mrdr_ref}"
                    )
                else:
                    products_no_match.append(unilever_ref or mrdr_ref)
        _logger.info(f"Products no match {products_no_match}")

    # flake8: noqa: C901
    def action_import(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_("Debe seleccionar un archivo para importar"))
        xl_workbook = False
        xl_sheet = False
        if self.filename.split(".")[1] in ["xls", "xlsx", "ods"]:
            xl_workbook = xlrd.open_workbook(
                file_contents=base64.b64decode(self.data_file)
            )
            xl_sheet = xl_workbook.sheet_by_index(0)
        if self.import_type == "pricelist":
            self._import_pricelist(xl_sheet)
        elif self.import_type == "grupos_turismo":
            self._import_grupos_turismo(xl_workbook)
        elif self.import_type == "discounts":
            self._import_discounts(xl_sheet)
        elif self.import_type == "inventory":
            self._import_inventory(xl_sheet)
        elif self.import_type == "gira":
            self._import_gira(xl_workbook)
        elif self.import_type == "change_uom":
            self.change_uom(xl_workbook)
        elif self.import_type == "update_supplierinfo":
            self._update_vendor_product_code(xl_workbook)
        elif self.import_type == "update_unilever_participation":
            self._update_unilever_participation(xl_workbook)
        elif self.import_type == "archive_virginia_partners":
            self._archive_virginia_partners(xl_workbook)
        elif self.import_type == "medios":
            self._import_medios(xl_workbook)
        elif self.import_type == "unilever_partner_update":
            self._unilever_partner_update(xl_workbook)
        elif self.import_type == "update_pol_price":
            self._update_pol_price(xl_workbook)
        elif self.import_type == "unilever_partner_sync":
            self._unilever_partner_sync(xl_workbook)
        elif self.import_type == "dto_rappel":
            self._import_dto_rappel(xl_workbook)
        elif self.import_type == "agreement_mef":
            self._import_agreement_mef(xl_workbook)
        elif self.import_type == "agreement_consumption":
            self._import_agreement_consumption(xl_workbook)
        elif self.import_type == "refund_unilever_mef":
            self._refund_unilever_mef(xl_workbook)
        elif self.import_type == "change_unilever_mef_moves_to_E":
            self._change_unilever_mef_moves_to_E(base64.b64decode(self.data_file))
        elif self.import_type == "unilever_mef_sn_to_scrap":
            self._unilever_mef_sn_to_scrap(xl_sheet)
        elif self.import_type == "unilever_uncheck_dto_settlements_lines":
            self._unilever_uncheck_dto_settlements_lines(xl_sheet)
        elif self.import_type == "match_pro_file":
            self._unilever_match_pro_file(xl_sheet)
        self.data_file = False
