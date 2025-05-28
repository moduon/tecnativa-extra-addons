#  Copyright 2020 Tecnativa - Sergio Teruel
#  Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class SettlementXlsx(models.AbstractModel):
    _name = "report.edi_backend_ulv.report_settlement_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Unilever report settlement xlsx"

    @api.model
    def create_report_dic(self, settlement_lines):
        id_liquidacion = self.env.context.get("id_liquidacion")
        total_dic = {}
        for line in settlement_lines:
            settlement = line.settlement_id
            is_bonus = settlement.unilever_settlement_type == "bonus"
            # TT31605. Agrupar por "codigo_cliente / Codigo_cadena"
            partner_chain = line.settlement_id.partner_id.company_group_id
            partner = partner_chain or line.settlement_id.partner_id
            detail_key = (partner, line.unilever_rappel_group_id)
            subtotal_key = line.unilever_rappel_group_id
            if not total_dic:
                total_dic = {
                    "codigo_concesionario": settlement.company_id.unilever_dealer,
                    "nombre_concesionario": settlement.company_id.name,
                    "tipo_registro": "Total",
                    "id_liquidacion": id_liquidacion,
                    "fecha_liquidacion": settlement.date.strftime("%d/%m/%Y"),
                    "ejercicio": settlement.date_to.year,
                    "periodo_liquidado": "{:%d/%m/%Y} a {:%d/%m/%Y}".format(
                        settlement.date_from or fields.Date.today(), settlement.date_to
                    ),
                    "tipo_liquidacion": "Bonificación" if is_bonus else "Dto factura",
                    "descuento_aplicado": 0,
                    "consumo": 0,
                    "bonificación": 0,
                    "iva_igic": 0,
                    "importe_contribucion": 0,
                    "contribucion": 0,
                    "codigo_cliente": 0,
                    "subtotal_dic": {},
                }
            subtotal_dic = total_dic["subtotal_dic"]
            if subtotal_key not in subtotal_dic:
                subtotal_dic[subtotal_key] = total_dic.copy()
                subtotal_dic[subtotal_key].update(
                    {
                        "tipo_registro": "Subtotal",
                        "iva_igic": 10,
                        "subgrupo_rappel": line.unilever_rappel_group_id.unilever_ref
                        or "",
                        "grupo_rappel": line.unilever_rappel_group_id.parent_id.unilever_ref  # noqa: B950 E501
                        or "",
                        "descuento_aplicado": 0,
                        "consumo": 0,
                        "bonificación": 0,
                        "importe_contribucion": 0,
                        "detail_dic": {},
                    }
                )
            detail_dic = subtotal_dic[subtotal_key]["detail_dic"]
            if detail_key not in detail_dic:
                detail_dic[detail_key] = subtotal_dic[subtotal_key].copy()
                detail_dic[detail_key].update(
                    {
                        "tipo_registro": "Detalle",
                        "codigo_cliente": int(
                            partner.company_group_id.unilever_ref
                            or partner.unilever_ref
                        ),
                        "nombre_cliente": partner.display_name[:70],
                        "direccion": partner.street,
                        "nif": partner.vat and partner.vat[-9:] or "",
                        "descuento_aplicado": line.percent,
                        "consumo": 0,
                        "bonificación": 0,
                        "contribucion": line.unilever_participation_percent,
                        "importe_contribucion": 0,
                    }
                )
                # TT31605
                # Overwrite codigo_cliente with dealer chain if agreement has
                # checked chain field
                # if line.agreement_id.chain and int(partner.unilever_dealer_chain):
                #     detail_dic[detail_key]["codigo_cliente"] = int(
                #         partner.unilever_dealer_chain
                #     )
            for dic_to_update in [
                total_dic,
                subtotal_dic[subtotal_key],
                detail_dic[detail_key],
            ]:
                dic_to_update["consumo"] += round(
                    (line.amount_invoiced if is_bonus else line.amount_gross), 2
                )
                dic_to_update["bonificación"] += round(line.amount_rebate, 2)
                dic_to_update["importe_contribucion"] += round(
                    line.unilever_contribution_amount, 2
                )
        return total_dic

    @api.model
    def write_line(self, sheet, row_index, line, columns_list):
        for col_index, col in enumerate(columns_list):
            if col in line:
                sheet.write(row_index, col_index, line[col])

    @api.model
    def generate_xlsx_report(self, workbook, data, settlement_lines):
        if not settlement_lines:
            return
        sheet = workbook.add_worksheet("Report")
        report_dic = self.create_report_dic(settlement_lines)
        columns_list = [
            "codigo_concesionario",
            "nombre_concesionario",
            "tipo_registro",
            "id_liquidacion",
            "fecha_liquidacion",
            "ejercicio",
            "periodo_liquidado",
            "tipo_liquidacion",
            "consumo",
            "bonificación",
            "importe_contribucion",
            "iva_igic",
            "contribucion",
            "subgrupo_rappel",
            "grupo_rappel",
            "codigo_cliente",
            "nombre_cliente",
            "direccion",
            "nif",
            "descuento_aplicado",
        ]
        # Header
        row_index = 0
        for col_index, col in enumerate(columns_list):
            sheet.write(row_index, col_index, col)
        # Total row
        row_index += 1
        self.write_line(sheet, row_index, report_dic, columns_list)
        subtotal_list = sorted(
            report_dic["subtotal_dic"].values(),
            key=lambda ln: (ln["grupo_rappel"], ln["subgrupo_rappel"]),
        )
        for subtotal_dic in subtotal_list:
            # Subtotal row
            row_index += 1
            self.write_line(sheet, row_index, subtotal_dic, columns_list)
        detail_list = []
        for subtotal_dic in subtotal_list:
            detail_list.extend(subtotal_dic["detail_dic"].values())
        detail_list.sort(
            key=lambda ln: (
                ln["codigo_cliente"],
                ln["grupo_rappel"],
                ln["subgrupo_rappel"],
            )
        )
        for detail_dic in detail_list:
            # Detail row in subtotal group
            row_index += 1
            self.write_line(sheet, row_index, detail_dic, columns_list)
