#  Copyright 2022 Tecnativa - Carlos Roca
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
import base64
import logging
from datetime import datetime
from io import BytesIO

import xlrd
import xlwt

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round

logger = logging.getLogger(__name__)


class EdiBackendMixin(models.AbstractModel):
    _inherit = "edi.backend.mixin"

    unilever_state = fields.Selection(
        selection=[
            ("not_sent", "Not sent"),
            ("sent", "Sent"),
            ("sent_error", "Errors"),
            ("cancelled", "Cancelled"),
        ],
        string="Backend state ULV",
        readonly=True,
        copy=False,
        help="Indicates the state of the Backend send state",
        default="not_sent",
    )

    def ulv_action_backend_sent(self):
        self.write({"unilever_state": "sent"})

    def ulv_action_backend_not_sent(self):
        self.write({"unilever_state": "not_sent"})

    def ulv_action_backend_sent_error(self):
        self.write({"unilever_state": "sent_error"})

    def ulv_action_backend_cancelled(self):
        self.write({"unilever_state": "cancelled"})


class EdiBackend(models.Model):
    _inherit = "edi.backend"

    provider = fields.Selection(
        selection_add=[("ulv", "Unilever")], ondelete={"ulv": "set base"}
    )
    force_year_ulv = fields.Integer(
        string="Force year", help="Only used for send DTO agreements"
    )
    dealer_code_ulv = fields.Char(
        string="Dealer code",
        help="If not filled Odoo will use the dealer code from company",
        size=10,
    )
    communication_code_ulv = fields.Char(
        string="Communication code",
        help="If not filled Odoo will use the communication code from company",
        size=5,
    )
    date_range = fields.Selection(
        selection_add=[("current_year", "This year")],
        ondelete={"current_year": "cascade"},
    )
    filename = fields.Char()

    def get_relative_date(self, date=False):
        if self.date_range != "current_year":
            return super().get_relative_date(date=date)
        year = fields.Date.today().year
        date_from = fields.Date.from_string(f"{year}-01-01")
        date_to = fields.Date.from_string(f"{year+1}-01-01")
        if self.date_field.ttype == "datetime":
            date_from = date_from.strftime("%Y-%m-%d 00:00:00")
            date_to = date_to.strftime("%Y-%m-%d 00:00:00")
        else:
            date_from = date_from.strftime("%Y-%m-%d")
            date_to = date_to.strftime("%Y-%m-%d")
        return date_from, date_to

    def _get_purchase_order(self, vals):
        PurchaseOrder = self.env["purchase.order"]
        # First search by Odoo PO number
        purchase = PurchaseOrder.search(
            [("name", "=", vals["Numero pedido concesionario"].lstrip("0"))]
        )
        if not purchase:
            purchase = PurchaseOrder.search(
                [("partner_ref", "=", vals["Numero de documento"].lstrip("0"))]
            )
        return purchase

    def _get_payment_invoice(self, vals):
        UnileverInvoiceRefund = self.env["unilever.invoice.refund"]
        payment_invoice = UnileverInvoiceRefund.search(
            [("name", "=", vals["Factura"].lstrip("0"))]
        )
        if not payment_invoice:
            payment_invoice = UnileverInvoiceRefund.create(
                {"name": vals["Factura"].lstrip("0")}
            )
        return payment_invoice

    def _clean_stock_move_lines(self, picking):
        """Remove all sml without lot_id assigned.
        Asumimos que todos los productos que vienen de Unilever tienen seguimiento por
        número de lote
        """
        smls = picking.move_line_ids.filtered(lambda sml: not sml.lot_id)
        smls.unlink()

    def _get_odoo_product_from_abo_file(self, file_ref):
        """Do search in this order"""
        product = self.env["product.product"].browse()
        for field_name in ["unilever_mrdr_ref", "unilever_ref", "default_code"]:
            product = (
                self.env["product.product"]
                .with_context(active_test=False)
                .search(
                    [(field_name, "=", file_ref)],
                    limit=1,
                )
            )
            if product:
                break
        return product

    def fill_model_data(self, vals, index=0):
        """Overwrite this method to fill the data model."""
        res = super().fill_model_data(vals, index=index)
        if self.code == "ALC":
            purchase = self._get_purchase_order(vals)
            if not purchase:
                logger.info(
                    "No purchase found for ULV purchase code: %s"
                    % vals["Numero de documento"]
                )
                return False
            # The customer never confirm th PO before than
            # Unilever have ben send the piking.
            # We need confirm the PO if not do it yet
            purchase.button_confirm()
            picking = purchase.picking_ids.filtered(
                lambda p: p.state in ("assigned", "confirmed")
            )[:1]
            if not picking:
                logger.info("No picking found for picking: %s" % picking.name)
                return False
            # Clean sml lines without lot
            self._clean_stock_move_lines(picking)
            product_code = vals["Producto"].lstrip("0")
            product = self.env["product.product"].search(
                [
                    "|",
                    ("unilever_mrdr_ref", "=", product_code),
                    ("unilever_ref", "=", product_code),
                ]
            )
            if not product:
                logger.info(
                    "No product found for ULV product code: %s" % (vals["Producto"])
                )
                return False
            if len(product) > 1:
                text_error = (
                    _("Next products has the same MRDR ref %s:\n") % product_code
                )
                for p in product:
                    text_error += f"\n\t- {p.display_name}"
                raise UserError(text_error)
            stock_move = picking.move_lines.filtered(
                lambda sm: sm.product_id == product
            )
            if not stock_move:
                price = (
                    product._select_seller(partner_id=purchase.partner_id).price
                    or product.standard_price
                )
                purchase.write(
                    {
                        "order_line": [
                            (
                                0,
                                0,
                                {
                                    "product_id": product.id,
                                    "name": product.display_name,
                                    "product_qty": 1.0,
                                    "product_uom": product.uom_id.id,
                                    "price_unit": price,
                                    "date_planned": picking.scheduled_date,
                                },
                            )
                        ]
                    }
                )
                stock_move = picking.move_lines.filtered(
                    lambda sm: sm.product_id == product
                )
            expiration_date = datetime.strptime(
                vals["Fecha de caducidad"], "%Y%m%d"
            ).date()
            lot_name = vals["Numero de Lote"].strip()
            StockProductionLot = self.env["stock.production.lot"]
            lot = StockProductionLot.search(
                [
                    ("product_id", "=", product.id),
                    ("name", "=", lot_name),
                    ("company_id", "=", picking.company_id.id),
                ]
            )
            if not lot:
                lot = StockProductionLot.create(
                    {
                        "name": lot_name,
                        "product_id": product.id,
                        "company_id": picking.company_id.id,
                        "expiration_date": expiration_date,
                    }
                )
            location_dest_id = (
                picking.location_dest_id._get_putaway_strategy(product)
                or picking.location_dest_id
            )
            self.env["stock.move.line"].create(
                {
                    "picking_id": picking.id,
                    "move_id": stock_move[:1].id,
                    "company_id": picking.company_id.id,
                    "product_id": product.id,
                    "product_uom_id": stock_move.product_uom.id or product.uom_id.id,
                    "qty_done": self._parse_stock_move_line_qty(
                        product, int(vals["Cantidad"])
                    ),
                    "lot_id": lot.id,
                    "lot_name": lot.name,
                    "location_id": picking.location_id.id,
                    "location_dest_id": location_dest_id.id,
                    "edi_unilever_sequence_file": index,
                }
            )
            return stock_move[:1].id
        if self.code == "PRO":
            # Procesado de fichero de productos
            if vals["Es_Main_DU"] != "X":
                return self.env["product.template"].browse()
            codigo_producto = vals["Codigo de producto"].lstrip("0")
            products = (
                self.env["product.template"]
                .with_context(active_test=False)
                .search(
                    [
                        ("unilever_ref", "=", vals["Codigo 5 cifras"].lstrip("0")),
                        ("unilever_mrdr_ref", "!=", codigo_producto),
                    ]
                )
            )
            if products:
                products.write({"unilever_mrdr_ref": codigo_producto})
            return products[:1].id
        if self.code == "ABO":
            payment_invoice = self._get_payment_invoice(vals)
            product = self._get_odoo_product_from_abo_file(
                vals["Referencia"].lstrip("0")
            )
            albaran = vals["Albaran"]
            picking = self.env["stock.picking"].search(
                [
                    ("picking_type_id", "=", int(albaran[:2])),
                    ("name", "like", "%%/%s" % int(albaran[2:])),
                ]
            )
            payment_invoice_line = self.env["unilever.invoice.refund.line"].create(
                {
                    "invoice_id": payment_invoice.id,
                    "line_type": vals["Tipo"],
                    "week": int(vals["Semana"][-2:]),
                    "year": int(vals["Semana"][:-2]),
                    "product_id": product.id,
                    "quantity": float(vals["Cantidad"]),
                    "price": float(vals["Tarifa"]) / 100,
                    "tpr": float(vals["TPR"]) / 100,
                    "dto_conces": float(vals["Dto. Conces."]) / 100,
                    "dto_early_pay": float(vals["Dto. pronto pago"]) / 100,
                    "dto_volume": float(vals["Dto. Volumen"]) / 100,
                    "amount_to_invoice": (float(vals["Tarifa"]) / 100)
                    - (float(vals["Importe abono producto"]) / 100),
                    "amount_line": float(vals["Importe abono producto"]) / 100,
                    "amount_distribution": float(vals["Importe Gastos distribucion"])
                    / 100,
                    "picking_id": picking.id,
                    "invoice_number": vals["Factura"],
                }
            )
            return payment_invoice_line.id
        return res

    def _parse_stock_move_line_qty(self, product, quantity):
        """TT40842"""
        unit_uom = self.env.ref("uom.product_uom_unit")
        qty_factor = product.format_id.product_qty or 1.0
        if product.uom_id != unit_uom:
            return quantity
        return float_round(quantity * qty_factor, precision_rounding=unit_uom.rounding)

    def xlsx2xls(self, content):
        rbook = xlrd.open_workbook(file_contents=content)
        wbook = xlwt.Workbook()
        for sheet in rbook.sheets():
            newsheet = wbook.add_sheet(sheet.name)
            for row in range(0, sheet.nrows):
                for col in range(0, sheet.ncols):
                    newsheet.write(row, col, sheet.cell_value(row, col))
        fp = BytesIO()
        wbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    def _get_file_wiz_context(self, sequence_file, anonymized_records):
        ctx = super()._get_file_wiz_context(sequence_file, anonymized_records)
        ctx.update(
            detail_dic={},
            start_date=fields.Date.from_string("2019-01-01"),
            end_date=fields.Date.today(),
            code=self.code,
            agreement_year=self.force_year_ulv or fields.Date.today().year,
            communication_code_ulv=self.communication_code_ulv
            or self.env.company.unilever_comunication_code,
            dealer_code_ulv=self.dealer_code_ulv or self.env.company.unilever_dealer,
        )
        if self.code == "MEF":
            last_inventory_move = self.env["stock.move"].search(
                [
                    ("product_id.is_unilever_mef", "=", True),
                    ("state", "=", "done"),
                    ("is_inventory", "=", True),
                ],
                limit=1,
                order="date",
            )
            ctx.update(last_inventory_move_date=last_inventory_move.date)
        return ctx

    def _get_export_data(self, domain, records, anonymized_records, sequence_file):
        if self.code == "LIQUIDACION-DTO":
            report = self.with_context(id_liquidacion=sequence_file).env.ref(
                "edi_backend_ulv.settlement_xlsx"
            )
            contents = report.with_context(
                active_model="agreement.settlement.line"
            )._render_xlsx(records.ids, {})
            file = base64.b64encode(self.xlsx2xls(contents[0]))
            file_name = "{}_liquidacion_{:%d%m%Y}{}.xls".format(
                self.company_id.unilever_dealer,
                records[:1].settlement_id.date,
                sequence_file,
            )
            return contents, file, file_name
        else:
            return super()._get_export_data(
                domain, records, anonymized_records, sequence_file
            )

    def _get_backend_filename(self, contents, sequence_file, records):
        if self.filename:
            return self.filename + self.extension
        if self.provider == "ulv":
            lines_count = contents.count(b"\n")
            return "{}{}{:04d}.{}".format(
                self.company_id.unilever_dealer,
                self.code.split("-")[0],
                lines_count,
                sequence_file,
            )
        return super()._get_backend_filename(contents, sequence_file, records)

    def get_data_ufs_to_print(self):
        """Special method to get the lines that has to be added to ufs file."""
        # Header of the file
        lines = [
            {
                "line": " Ejercicio ; Concesionario ; Cliente ; Producto ;"
                + " Descuento ; Euros ; Desde ; Hasta ; Participacion ;"
            }
        ]
        actual_year = fields.Date.today().year
        ProductProduct = self.env["product.product"]
        # Get products of rappel with code 116
        product_foods = ProductProduct.search(
            [("unilever_rappel_group_id.code", "=", "116")]
        )
        categ_foods = product_foods.categ_id
        # Filter pricelists that have been active during this year
        pricelist_items = self.env["product.pricelist.item"].search(
            [
                "|",
                ("date_start", "=", False),
                ("date_start", "<=", fields.Datetime.now()),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", str(actual_year) + "-01-01 00:00:00"),
                "|",
                ("product_id", "in", product_foods.ids),
                "|",
                ("product_tmpl_id", "in", product_foods.product_tmpl_id.ids),
                ("categ_id", "in", categ_foods.ids),
            ]
        )
        pricelists = pricelist_items.pricelist_id
        # Get partners that has this pricelists defined (module partner_pricelist_search
        # is needed)
        partners = self.env["res.partner"].search(
            [
                ("property_product_pricelist", "in", pricelists.ids),
                ("unilever_ref", "!=", False),
            ]
        )
        for partner in partners:
            # The start of the line will be the same for all pricelist items of this
            # partner
            base_line = " {} ; {} ; {} ;".format(
                str(actual_year), self.env.company.unilever_dealer, partner.unilever_ref
            )
            partner_pricelist_items = pricelist_items.filtered(
                lambda pi, p=partner: pi.pricelist_id == p.property_product_pricelist
            )
            partner_pricelist_items = partner_pricelist_items.sorted("applied_on")
            visited_products = ProductProduct
            for pricelist_item in partner_pricelist_items:
                line = False
                if (
                    pricelist_item.applied_on[0] == "0"
                    and pricelist_item.product_id in product_foods
                ):
                    visited_products += pricelist_item.product_id
                    line = self._get_line_ufs(
                        base_line, pricelist_item.product_id, pricelist_item
                    )
                elif pricelist_item.applied_on[0] == "1":
                    for product in product_foods.filtered(
                        lambda p, pi=pricelist_item, vp=visited_products: p.product_tmpl_id
                        == pi.product_tmpl_id
                        and p not in vp
                    ):
                        visited_products += product
                        line = self._get_line_ufs(base_line, product, pricelist_item)
                elif pricelist_item.applied_on[0] == "2":
                    for product in product_foods.filtered(
                        lambda p, pi=pricelist_item, vp=visited_products: p.categ_id
                        == pi.categ_id
                        and p not in vp
                    ):
                        line = self._get_line_ufs(base_line, product, pricelist_item)
                if line:
                    lines.append({"line": line})
        return lines

    @api.model
    def _get_line_ufs(self, base_line, product, pricelist_item):
        """Method used to get the line that has to be added to ufs edi file."""
        actual_year = fields.Date.today().year
        discount = 0.0
        euros = 0.0
        if pricelist_item.compute_price == "fixed":
            euros = product.list_price - pricelist_item.fixed_price
        else:
            discount = (
                pricelist_item.percent_price
                if pricelist_item.compute_price == "percentage"
                else pricelist_item.price_discount
            )
        if float_is_zero(discount, precision_rounding=2) and float_is_zero(
            euros, precision_rounding=2
        ):
            return False
        return "{} {} ; {:.2f} ; {:.2f} ; {} ; {} ; 90.00 ;".format(
            base_line,
            product.unilever_ref,
            discount,
            euros,
            pricelist_item.date_start
            and pricelist_item.date_start.year == actual_year
            and pricelist_item.date_start.strftime("%d/%m/%Y")
            or "01/01/" + str(actual_year),
            pricelist_item.date_end
            and pricelist_item.date_end.year == actual_year
            and pricelist_item.date_end.strftime("%d/%m/%Y")
            or "31/12/" + str(actual_year),
        )


class EdiBackendCommunicationHistory(models.Model):
    _inherit = "edi.backend.communication.history"

    # Only for ALB file
    product_qty_out_ulv = fields.Float(
        string="Qty OUT",
        compute="_compute_amount_total",
        store=True,
        digits="Product Unit of Measure",
        readonly=True,
    )
    product_qty_in_ulv = fields.Float(
        string="Qty IN",
        compute="_compute_amount_total",
        store=True,
        digits="Product Unit of Measure",
        readonly=True,
    )
    amount_total_out_ulv = fields.Float(
        string="Amount total OUT",
        compute="_compute_amount_total",
        digits="Product Price",
        store=True,
        readonly=True,
    )
    amount_total_in_ulv = fields.Float(
        string="Amount total IN",
        compute="_compute_amount_total",
        store=True,
        digits="Product Price",
        readonly=True,
    )
    amount_total_ulv = fields.Float(
        string="Amount total",
        compute="_compute_amount_total",
        store=True,
        digits="Product Price",
        readonly=True,
    )
    invoice_line_ids_ulv = fields.Many2many(
        comodel_name="account.move.line",
        relation="account_move_line_backend_communication_history_rel",
        column1="communication_history_id",
        column2="invoice_line_id",
    )

    def _prepare_total_alb_domain(self, stock_moves):
        return [
            ("move_id", "in", stock_moves.ids),
            ("state", "=", "done"),
            ("qty_done", "!=", 0.0),
            ("product_id.seller_ids.name", "=", 42803),
            (
                "product_id.unilever_rappel_group_id.code",
                "not in",
                ("114", "115", "99"),
            ),
            ("product_id.product_brand_id.unilever_ref", "!=", False),
        ]

    @api.depends("applied_records")
    def _compute_amount_total(self):
        """
        Compute amount totals out and in based con product standard_price
        field for avery history line.
        This method only must be computed for ALB Unilever file which has not
        sale order lines linked.
        Issue: https://www.tecnativa.com/web#id=21026&model=project.task
               &view_type=form
        """
        StockMoveLine = self.env["stock.move.line"]
        Product = self.env["product.product"]
        precision_price = self.env["decimal.precision"].precision_get("Product Price")
        precision_uom = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )
        for history in self:
            if history.edi_backend_id.code != "ALB":
                continue
            records = history.get_applied_records()
            records_in = records.filtered("is_return")
            records_out = records - records_in

            move_lines_out = StockMoveLine.read_group(
                self._prepare_total_alb_domain(records_out),
                ["product_id", "qty_done"],
                ["product_id"],
                lazy=False,
            )
            move_lines_in = StockMoveLine.read_group(
                self._prepare_total_alb_domain(records_in),
                ["product_id", "qty_done"],
                ["product_id"],
                lazy=False,
            )

            product_qty_out = product_qty_in = 0.0
            amount_total = amount_total_out = amount_total_in = 0.0
            for move in move_lines_out:
                product = Product.browse(move["product_id"][0])
                qty = float_round(move["qty_done"], precision_digits=precision_uom)
                product_qty_out += qty
                amount_total_out += float_round(
                    qty * product.standard_price, precision_digits=precision_price
                )
            for move in move_lines_in:
                product = Product.browse(move["product_id"][0])
                qty = float_round(move["qty_done"], precision_digits=precision_uom)
                product_qty_in += qty
                amount_total_in += float_round(
                    qty * product.standard_price, precision_digits=precision_price
                )

            amount_total = amount_total_out - amount_total_in
            history.update(
                {
                    "product_qty_out_ulv": product_qty_out,
                    "product_qty_in_ulv": product_qty_in,
                    "amount_total_out_ulv": amount_total_out,
                    "amount_total_in_ulv": amount_total_in,
                    "amount_total_ulv": amount_total,
                }
            )
