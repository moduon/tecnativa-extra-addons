# Copyright 2004-2011 Luis Manuel Angueira Blanco (http://pexego.es)
# Copyright 2013 Ignacio Ibeas (http://acysos.com)
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2016 Angel Moya <odoo@tecnativa.com>
# Copyright 2019 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# This file is a copy of l10n.es.aeat.report.export_to_boe

import base64
import re

from dateutil.relativedelta import relativedelta

from odoo import _, exceptions, fields, models, tools
from odoo.tools.safe_eval import safe_eval

EXPRESSION_PATTERN = re.compile(r"(\$\{.+?\})")


class EdiBackendFileWiz(models.TransientModel):
    _name = "edi.backend.file.wiz"
    _description = "EDI Backend File Wizard"

    name = fields.Char(string="File name", readonly=True)
    data = fields.Binary(string="File", readonly=True)
    state = fields.Selection(
        selection=[("open", "open"), ("get", "get")], default="open"
    )

    # Modifify to don't transform to upper ('Ver')
    def _format_string(
        self, text, length, fill=" ", align="<", allow_special_character=False
    ):
        """Format the string into a fixed length ASCII (iso-8859-1) record.

        Note:
            'Todos los campos alfanuméricos y alfabéticos se presentarán
            alineados a la izquierda y rellenos de blancos por la derecha,
            en mayúsculas sin caracteres especiales, y sin vocales acentuadas.
            Para los caracteres específicos del idioma se utilizará la
            codificación ISO-8859-1. De esta forma la letra “Ñ” tendrá el
            valor ASCII 209 (Hex. D1) y la “Ç” (cedilla mayúscula) el valor
            ASCII 199 (Hex. C7).'
        """
        if not text:
            return fill * length
        # Replace accents and convert to upper
        from unidecode import unidecode

        # text = text.upper()
        if not allow_special_character:
            text = "".join([unidecode(x) if x not in ("Ñ", "Ç") else x for x in text])
            text = re.sub(
                r"[^A-Za-z0-9\s\.,-_&'´\\:;/\(\)ÑÇ\"]", "", text, re.UNICODE | re.X
            )
        ascii_string = text
        # Cut the string if it is too long
        if len(ascii_string) > length:
            ascii_string = ascii_string[:length]
        # Format the string
        ascii_fill = fill
        if align == "<":
            ascii_string = ascii_string.ljust(length, ascii_fill)
        elif align == ">":
            ascii_string = ascii_string.rjust(length, ascii_fill)
        else:
            assert False, _("Wrong align option. It should be < or >")  # noqa: B011
        # Sanity-check
        assert len(ascii_string) == length, _(
            "The formated string must match the given length: %s", ascii_string
        )
        # Return string
        return ascii_string

    def _format_alphabetic_string(
        self, text, length, fill=" ", align="<", allow_special_character=False
    ):
        """Format the string into a fixed length ASCII (iso-8859-1) record
        without numbers.
        """
        if not text:
            return fill * length
        # Replace numbers
        name = re.sub(r"[\d-]", "", text, re.UNICODE | re.X)
        return self._format_string(
            name,
            length,
            fill=fill,
            align=align,
            allow_special_character=allow_special_character,
        )

    # Modify to include dec_separator and change defaults
    def _format_number(
        self,
        number,
        int_length,
        dec_length=0,
        include_sign=False,
        positive_sign="",
        negative_sign="-",
        dec_separator=".",
        fill_with="zero",
    ):
        """Format the number into a fixed length ASCII (iso-8859-1) record.

        Note:
            'Todos los campos numéricos se presentarán alineados a la derecha
            y rellenos a ceros por la izquierda sin signos y sin empaquetar.'
            (http://www.boe.es/boe/dias/2008/10/23/pdfs/A42154-42190.pdf)
        """
        #
        # Separate the number parts (-55.23 => int_part=55,
        # dec_part=0.23, sign='N')
        #
        if number == "":
            number = 0.0
        number = float(number)
        sign = positive_sign if number >= 0 else negative_sign
        number = abs(number)
        int_part = int(number)
        # Format the string
        ascii_string = ""
        if include_sign:
            ascii_string += sign
        if dec_length > 0:
            ascii_string += "%0*.*f" % (
                int_length + dec_length + 1 - len(dec_separator),
                dec_length,
                number,
            )
            ascii_string = ascii_string.replace(".", dec_separator)
        elif int_length > 0:
            if fill_with == "blank":
                # Format number 0 as ' '
                if int_part:
                    ascii_string += "%*d" % (int_length, int_part)
                else:
                    ascii_string += "%*s" % (int_length, "")
            else:
                ascii_string += "%.*d" % (int_length, int_part)
        # Sanity-check
        assert len(ascii_string) == (
            (include_sign and len(sign) or 0) + int_length + dec_length
        ), _("The formated string must match the given length: %d") % (number)
        # Return the string assuring that is not unicode
        return str(ascii_string)

    def _format_boolean(self, value, yes="X", no=" "):
        """
        Format a boolean value into a fixed length ASCII (iso-8859-1) record.
        """
        res = value and yes or no
        # Return the string assuring that is not unicode
        return str(res)

    def _do_global_checks(self, record, contents):
        return True

    def action_get_file(self):
        """Action that exports the data into a BOE formatted text file.

        @return: Action dictionary for showing exported file.
        """
        active_id = self.env.context.get("active_id", False)
        active_model = self.env.context.get("active_model", False)
        if not active_id or not active_model:
            return False
        report = self.env[active_model].browse(active_id)
        contents = b""
        if report.export_config_id:
            contents += self.action_get_file_from_config(report)
        else:
            raise exceptions.UserError(_("No export configuration selected."))
        # Generate the file and save as attachment
        file = base64.encodestring(contents)
        file_name = _("%(report_number)s_report_%(today)s.txt") % {
            "report_number": report.number,
            "today": fields.Date.today(),
        }
        # Delete old files
        attachment_obj = self.env["ir.attachment"]
        attachment_ids = attachment_obj.search(
            [("name", "=", file_name), ("res_model", "=", report._name)]
        )
        attachment_ids.unlink()
        attachment_obj.create(
            {
                "name": file_name,
                "datas": file,
                "datas_fname": file_name,
                "res_model": report._name,
                "res_id": report.id,
            }
        )
        self.write({"state": "get", "data": file, "name": file_name})
        # Force view to be the parent one
        data_obj = self.env.ref("l10n_es_aeat.wizard_aeat_export")
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "view_id": [data_obj.id],
            "res_id": self.id,
            "target": "new",
        }

    def action_get_file_from_config(self, report):
        self.ensure_one()
        return self._export_config(report, report.export_config_id)

    def _export_config(self, obj, export_config):
        self.ensure_one()
        contents = b""
        for line in export_config.config_line_ids:
            contents += self._export_line_process(obj, line)
        return contents

    def _get_vals_for_safe_eval(self, obj):
        return {
            "user": self.env.user,
            "object": obj,
            "context": self.env.context.copy(),
            "today": fields.Date.today(),
            "format_date": self.format_custom_date,
            "format_date_sp": self.format_custom_date_sp,
            "format_hour": self.format_custom_hour,
            "relativedelta": relativedelta,
        }

    # Modify to include date functions
    def _export_line_process(self, obj, line):
        # usar esta variable para resolver las expresiones
        obj_merge = obj

        def merge_eval(exp):
            especific_obj = obj_merge
            if not isinstance(obj_merge, dict):
                especific_obj = obj_merge.with_context(**self.env.context)
            return safe_eval(
                exp,
                self._get_vals_for_safe_eval(especific_obj),
            )

        def merge(match):
            exp = str(match.group()[2:-1]).strip()
            result = merge_eval(exp)
            return result and tools.ustr(result) or ""

        val = b""
        if line.conditional_expression:
            if not merge_eval(line.conditional_expression):
                return val
        if line.repeat_expression:
            obj_list = merge_eval(line.repeat_expression)
        else:
            obj_list = [obj]
        for obj_merge in obj_list:
            if line.export_type == "subconfig":
                val += self._export_config(obj_merge, line.subconfig_id)
            else:
                if line.expression:
                    field_val = EXPRESSION_PATTERN.sub(merge, line.expression)
                else:
                    field_val = line.fixed_value
                anonymized = False
                if not isinstance(obj_merge, dict):
                    anonymized = (
                        line.anonymize_value
                        and obj_merge.id
                        in self.env.context.get("anonymized_records", [])
                    )
                record = self._export_simple_record(
                    line,
                    field_val,
                    anonymized=anonymized,
                    anonymize_char=self.env.context.get("anonymize_char", " "),
                )
                if isinstance(record, str):
                    record = record.encode(self.env.context.get("encode"))
                val += record
        return val

    def _export_simple_record(self, line, val, anonymized=False, anonymize_char=" "):
        line_size = self._get_line_size(line, val)
        if line.export_type == "string":
            # Modify to adjust val to size
            if anonymized:
                val = anonymize_char * line_size
            elif val and len(val) > line_size:
                val = val[:line_size]
            align = ">" if line.alignment == "right" else "<"
            value = self._format_string(
                val or "",
                line_size,
                align=align,
                allow_special_character=line.allow_special_character,
            )
        elif line.export_type == "boolean":
            value = self._format_boolean(val, line.bool_yes, line.bool_no)
        elif line.export_type == "alphabetic":
            if anonymized:
                val = anonymize_char * line_size
            align = ">" if line.alignment == "right" else "<"
            value = self._format_alphabetic_string(
                val or "",
                line_size,
                align=align,
                allow_special_character=line.allow_special_character,
            )
        else:  # float or integer
            if anonymized:
                val = 0
            decimal_size = 0 if line.export_type == "integer" else line.decimal_size
            fill_with = line.filler_zero_with or line.export_config_id.filler_zero_with
            number = float(val or 0)
            sign = line.negative_sign if number < 0.0 else line.positive_sign
            value = self._format_number(
                number,
                line_size - decimal_size - (line.apply_sign and len(sign or "") or 0),
                decimal_size,
                line.apply_sign,
                positive_sign=line.positive_sign or "",
                negative_sign=line.negative_sign,
                fill_with=fill_with,
            )
        return self._post_processed_value(line, value)

    def format_custom_date(self, date):
        date_str = fields.Date.to_string(date)
        return date_str.replace("-", "")[:8]

    def format_custom_hour(self, date):
        date_str = fields.Datetime.to_string(date)
        return date_str.replace(":", "")[-6:]

    def format_custom_date_sp(self, date):
        date_str = fields.Date.to_string(date)
        return "{0[8]}{0[9]}{0[5]}{0[6]}{0[0]}{0[1]}{0[2]}{0[3]}".format(date_str)

    def _get_line_size(self, line, val):
        if not line.export_config_id.columns_definition == "separator":
            return line.size
        line_size = line.size
        if line.export_type in ["string", "alphabetic"]:
            line_size = len(val or "")
        if line.export_type in ["integer", "float"]:
            len_int_part = len(str(abs(int(float(val or 0)))))
            sign = line.negative_sign if float(val or 0) < 0.0 else line.positive_sign
            line_size = (
                len_int_part
                + line.decimal_size
                + (line.apply_sign and len(sign or "") or 0)
            )
            if line.export_type == "float" and line.decimal_size:
                # Decimal point position
                line_size += 1
        return line_size

    def _post_processed_value(self, line, value):
        if (
            line.export_config_id.columns_definition == "separator"
            and line.export_config_id.separator_char
            and line.apply_separator_char
        ):
            if isinstance(value, bytes):
                value += line.export_config_id.separator_char.encode()
            else:
                value += line.export_config_id.separator_char
        return value
