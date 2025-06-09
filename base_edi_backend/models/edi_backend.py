# Copyright 2022 Tecnativa - Sergio Teruel
# Copyright 2022 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
import ast
import base64
import json
import logging
from io import BytesIO

import pysftp
from dateutil.relativedelta import relativedelta

from odoo import _, api, exceptions, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)
try:
    import ftplib
except ImportError:
    _logger.debug("Cannot import ftplib")


class EdiBackend(models.Model):
    _name = "edi.backend"
    _description = "EDI Backend"
    _inherit = ["mail.alias.mixin", "mail.thread"]

    active = fields.Boolean(default=True)
    name = fields.Char()
    code = fields.Char()
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Sequence file",
    )
    # The module will work as it is. However, some providers might override some things
    provider = fields.Selection(selection=[("base", "Generic")], required=True)
    communication_type = fields.Selection(
        selection=[("ftp", "FTP"), ("sftp", "SFTP"), ("email", "E-Mail")],
        default="ftp",
        required=True,
    )
    action_type = fields.Selection(
        selection=[("export", "Export"), ("import", "Import")],
        default="export",
        required=True,
    )
    register_record_state = fields.Boolean(
        help="If set the record state will be set on every backend communication",
    )
    sequence_number_next = fields.Integer(
        related="sequence_id.number_next_actual",
        string="Next sequence",
        readonly=False,
    )
    last_sync_date = fields.Datetime(
        string="Last Export", default="2000-01-01 00:00:00"
    )
    export_config_id = fields.Many2one(
        comodel_name="edi.backend.config",
        string="Export config",
        ondelete="cascade",
    )
    import_config_id = fields.Many2one(
        comodel_name="edi.backend.config",
        string="Import config",
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Odoo model",
    )
    filter_domain = fields.Char(string="Apply on")
    model_name = fields.Char()
    special_domain = fields.Char(
        compute="_compute_special_domain",
        string="Special domain",
    )
    date_field = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Date field to filter",
    )
    date_range = fields.Selection(
        selection=[("current_month", "Current Month"), ("last_month", "Last Month")],
        string="Date Field Range",
    )
    security_days = fields.Integer(string="Security days")
    data = fields.Binary(string="Last File", readonly=True)
    extension = fields.Char(
        default=".txt",
    )
    file_name = fields.Char(string="File name")
    # FTP data
    ftp_host = fields.Char()
    ftp_user = fields.Char()
    ftp_password = fields.Char()
    ftp_file_special_name = fields.Char(
        string="File Special Name",
        help="File will allways be synced with this name",
    )
    # SFTP data
    sftp_host = fields.Char()
    sftp_user = fields.Char()
    sftp_password = fields.Char()
    sftp_port = fields.Integer(default=22)
    sftp_file_special_name = fields.Char(
        string="File Special Name",
        help="File will allways be synced with this name",
    )
    remote_path = fields.Char(string="Remote path")
    # Mail data
    destination_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        help="When mailing is enabled these will be the partners we'll communicate to",
    )
    email_author = fields.Many2one(
        comodel_name="res.partner",
    )
    # Communication history
    history_count = fields.Integer(compute="_compute_history_count")
    group_key = fields.Char(
        string="Group key",
    )
    anonymize_entries = fields.Boolean()
    anonymized_domain = fields.Char()
    char_for_anonymize = fields.Char(default="x", size=1)
    notes = fields.Html()
    encoding = fields.Char(default="iso-8859-1", required=True)
    fill_model_data_one_record = fields.Boolean()

    @api.depends("date_field", "date_range", "last_sync_date", "security_days")
    def _compute_special_domain(self):
        """Relative dates to every sync"""
        self.special_domain = False
        for edi in self:
            if not edi.date_field:
                edi.special_domain = False
                continue
            domain = []
            if edi.security_days:
                domain.extend([(edi.date_field.name, "<", edi.get_relative_date())])
            elif edi.date_range:
                dates = edi.get_relative_date()
                domain.extend(
                    [
                        (edi.date_field.name, ">=", dates[0]),
                        (edi.date_field.name, "<", dates[1]),
                    ]
                )
            edi.special_domain = str(domain)

    def get_relative_date(self, date=False):
        if self.security_days:
            security_date = date or fields.Date.today()
            return fields.Date.to_string(
                fields.Date.from_string(security_date)
                - relativedelta(days=self.security_days)
            )
        today = fields.Date.today()
        if not self.date_range:
            return (today, today)
        date_from = date_to = fields.Date.from_string(today)
        if self.date_range == "last_month":
            date_from = fields.Date.from_string(today) - relativedelta(months=1)
        elif self.date_range == "current_month":
            date_to = fields.Date.from_string(today) + relativedelta(months=1)
        if self.date_field.ttype == "datetime":
            date_from = date_from.strftime("%Y-%m-01 00:00:00")
            date_to = date_to.strftime("%Y-%m-01 00:00:00")
        else:
            date_from = date_from.strftime("%Y-%m-01")
            date_to = date_to.strftime("%Y-%m-01")
        return (date_from, date_to)

    def _compute_history_count(self):
        for edi in self:
            edi.history_count = self.env[
                "edi.backend.communication.history"
            ].search_count([("edi_backend_id", "=", edi.id)])

    def get_records(self):
        domain = (
            self.env.context.get("applied_domain", False) or self.get_complete_domain()
        )
        records = self.env[self.model_id.model].search(domain)
        return records

    def get_mapped_records(self, mapped_field):
        records = self.get_records()
        records = records.mapped(mapped_field)
        return records

    @api.onchange("model_id")
    def onchange_model_id(self):
        self.model_name = self.model_id.model

    def action_export(self):
        self.data = False
        self.action_export_run()

    def action_import(self):
        self.data = False
        self.action_import_run()

    def _get_vals_from_file(self, history=False):
        vals_list = []
        if history:
            file = base64.b64decode(history.data)
        else:
            file = base64.b64decode(self.data)
        file_string = file.decode("iso-8859-15")
        file_array = file_string.split("\n")
        if self.import_config_id.columns_definition == "separator":
            for item in file_array:
                if not item:
                    continue
                vals_list.append(item.split(self.import_config_id.separator_char))
        else:
            lines_config = self.import_config_id.config_line_ids
            for item in file_array:
                if not item:
                    continue
                vals = {}
                for config in lines_config:
                    value = item[
                        config.position - 1 : config.position + config.size - 1
                        if config.size
                        else None
                    ]
                    vals[config.key] = value
                if vals:
                    vals_list.append(vals)
        return vals_list

    def _fill_data_from_vals(self, vals_list):
        records = set()
        last_record_id = False
        if self.fill_model_data_one_record:
            records.add(self.fill_model_data(vals_list))
        else:
            for index, vals in enumerate(vals_list):
                rec = self.with_context(last_record_id=last_record_id).fill_model_data(
                    vals, index
                )
                if rec:
                    last_record_id = rec
                    records.add(rec)
        return list(records)

    def fill_model_data(self, vals, index=0):
        """Overwrite this method to fill the data model."""
        return False

    def create_cron(self):
        IrCron = self.env["ir.cron"]
        if self.provider != "base":
            name = "[{}] EDI Backend {}".format(self.provider.upper(), self.name)
        else:
            name = "EDI Backend {}".format(self.name)
        ir_cron = IrCron.with_context(active_test=False).search(
            [("edi_backend_id", "=", self.id)]
        )
        if not ir_cron:
            ir_cron = self.env["ir.cron"].create(
                {
                    "name": name,
                    "model_id": self.env.ref("base_edi_backend.model_edi_backend").id,
                    "state": "code",
                    "interval_number": 1,
                    "interval_type": "weeks",
                    "numbercall": -1,
                    "edi_backend_id": self.id,
                }
            )
        if self.action_type == "export":
            ir_cron.write(
                {"code": "model.browse({}).action_export_job()".format(self.id)}
            )
        elif self.action_type == "import":
            ir_cron.write(
                {"code": "model.browse({}).action_import_job()".format(self.id)}
            )
        action = self.env["ir.actions.act_window"]._for_xml_id("base.ir_cron_act")
        if len(ir_cron) == 1:
            form = self.env.ref("base.ir_cron_view_form")
            action["views"] = [(form.id, "form")]
            action["res_id"] = ir_cron.id
        else:
            action["domain"] = [("id", "in", ir_cron.ids)]
        return action

    def action_communication_history(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "base_edi_backend.action_edi_backend_communication_history"
        )
        action["domain"] = [("edi_backend_id", "=", self.id)]
        return action

    def action_export_job(self):
        self.with_delay().action_export_run()

    def action_import_job(self):
        self.with_delay().action_import_run()

    def get_complete_domain(self):
        domain = safe_eval(self.filter_domain)
        if self.special_domain:
            domain.extend(safe_eval(self.special_domain))
        return domain

    def get_anonymize_domain(self):
        return safe_eval(self.anonymized_domain or "[]")

    def _get_anonymized_records(self):
        anonymized_records = []
        if self.anonymize_entries:
            domain = self.get_anonymize_domain()
            anonymized_records = self.env[self.model_name].search(domain).ids
        return anonymized_records

    def _get_file_wiz_context(self, sequence_file, anonymized_records):
        return {
            "active_model": self._name,
            "active_id": self.id,
            "today": fields.Date.today(),
            "sequence_file": sequence_file,
            "anonymized_records": anonymized_records,
            "anonymize_char": self.char_for_anonymize,
            "encode": self.encoding,
        }

    def _get_export_data(self, domain, records, anonymized_records, sequence_file):
        WizExport = self.env["edi.backend.file.wiz"]
        ctx = self._get_file_wiz_context(sequence_file, anonymized_records)
        vals = {"name": "File {}".format(self.name)}
        wiz_export = WizExport.with_context(**ctx).create(vals)
        contents = b""
        contents += wiz_export.with_context(
            applied_domain=domain
        ).action_get_file_from_config(self)
        # Generate the file and save as attachment
        file = base64.b64encode(contents)
        file_name = self._get_backend_filename(contents, sequence_file, records)
        return contents, file, file_name

    def action_export_run(self, history_line=False):
        if not self.export_config_id:
            raise exceptions.UserError(_("No export configuration selected."))
        if history_line:
            domain = safe_eval(history_line.applied_domain)
        else:
            domain = self.get_complete_domain()
        records = self.with_context(applied_domain=domain).get_records()
        now = fields.Datetime.now()
        if not records:
            return
        anonymized_records = self._get_anonymized_records()
        # Get sequence and write it in context to be used in content file
        sequence_file = (
            history_line
            and history_line.applied_sequence
            or self.sequence_id.next_by_id()
        )
        contents, file, file_name = self._get_export_data(
            domain,
            records,
            anonymized_records,
            sequence_file,
        )
        if not history_line or self.env.context.get("force_save_last_export_file"):
            self.write(
                {
                    "data": file,
                    "file_name": file_name,
                    "last_sync_date": self.security_days
                    and self.get_relative_date()
                    or now,
                }
            )
        # When adding an extra sending option, we'll add the proper method
        getattr(self, "send_file_by_%s" % self.communication_type)(file, file_name)
        if history_line:
            history_line.write(
                {
                    "state": "sent",
                    "data": file,
                    "file_name": file_name,
                    "applied_records": records.ids,
                }
            )
        else:
            history_line = self.env["edi.backend.communication.history"].create(
                {
                    "edi_backend_id": self.id,
                    "state": "sent",
                    "applied_domain": domain,
                    "applied_records": records.ids,
                    "applied_sequence": sequence_file,
                    "data": file,
                    "file_name": file_name,
                }
            )
        # In order to be able use record state the model should have edi.backend.mixin
        # Every provider should have their proper wildcard methods declared.
        if self.register_record_state and hasattr(
            records, "%s_action_backend_sent" % self.provider
        ):
            getattr(records, "%s_action_backend_sent" % self.provider)()
        return history_line

    def action_import_one_file(self, file_name):
        file = getattr(self, "_file_from_%s" % self.communication_type)(file_name)
        history = self.env["edi.backend.communication.history"].create(
            {
                "edi_backend_id": self.id,
                "company_id": self.company_id.id,
                "data": file,
                "file_name": file_name,
            }
        )
        vals_list = self._get_vals_from_file(history=history)
        record_ids = self._fill_data_from_vals(vals_list)
        history.applied_records = str(record_ids)
        # If no problems found, then delete files from server
        getattr(self, "_%s_delete_file" % self.communication_type)(file_name)

    def action_import_run(self):
        fields.Datetime.now()
        if self.communication_type == "email":
            self.action_import_history_run()
        else:
            file_names = getattr(self, "_%s_get_names" % self.communication_type)()
            if len(file_names) == 1:
                self.action_import_one_file(file_names[0])
            else:
                # queue a job for each file
                for file_name in file_names:
                    self.with_delay().action_import_one_file(file_name)

    def _get_backend_filename(self, contents, sequence_file, records):
        lines_count = contents.count(b"\n")
        return "{}{}{}{}".format(
            self.code,
            lines_count,
            sequence_file,
            self.extension,
        )

    # FTP Connection methods
    def _ftp_connection_params(self):
        return {
            "host": self.ftp_host,
            "user": self.ftp_user,
            "passwd": self.ftp_password,
        }

    def action_ftp_test_connection(self):
        """Check if the ftp settings are correct."""
        try:
            with self._ftp_connection() as ftp:
                if ftp.getwelcome():
                    raise exceptions.UserError(_("Connection Test OK!"))
        except exceptions.UserError:
            raise
        except Exception:
            raise exceptions.ValidationError(
                _("Connection Test Failed! %s") % Exception
            ) from Exception

    def _ftp_connection(self):
        """Return a new FTP connection with found parameters."""
        _logger.debug(
            "Trying to connect to ftp://%(user)s@%(host)s",
            extra=self._ftp_connection_params(),
        )
        ftp = ftplib.FTP(**self._ftp_connection_params())
        _logger.info("Connected to sftp://{}".format(self.ftp_user))
        return ftp

    def _file_to_ftp(self, file_name, data):
        if not (data and self.data):
            return
        with self._ftp_connection() as ftp:
            ftp.cwd(self.remote_path)
            file = base64.b64decode(data or self.data)
            ftp.storbinary("STOR " + file_name, BytesIO(file))

    def send_file_by_ftp(self, file, file_name):
        if not self.ftp_host or not self.ftp_user:
            return
        ftp_file_name = self.ftp_file_special_name or file_name
        self._file_to_ftp(ftp_file_name, file)

    # SFTP Connection methods
    def _sftp_connection_params(self):
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        return {
            "host": self.sftp_host,
            "username": self.sftp_user,
            "password": self.sftp_password,
            "port": self.sftp_port,
            "cnopts": cnopts,
        }

    def action_sftp_test_connection(self):
        """Check if the ftp settings are correct."""
        try:
            with self._sftp_connection() as sftp:
                if sftp.pwd:
                    raise exceptions.UserError(_("Connection Test OK!"))
        except exceptions.UserError:
            raise
        except Exception:
            raise exceptions.ValidationError(
                _("Connection Test Failed! %s") % Exception
            ) from Exception

    def _sftp_connection(self):
        """Return a new SFTP connection with found parameters."""
        values = self._sftp_connection_params()
        _logger.debug("Trying to connect to sftp://%(user)s@%(host)s", extra=values)
        sftp = pysftp.Connection(**values)
        _logger.info("Connected to sftp://{}".format(self.sftp_user))
        return sftp

    def _file_to_sftp(self, file_name, data):
        if not (data or self.data):
            return
        with self._sftp_connection() as sftp:
            remote_path = self.remote_path or ""
            if not self.remote_path or self.remote_path[-1] != "/":
                remote_path += "/"
            file = base64.b64decode(data or self.data)
            sftp.putfo(BytesIO(file), remotepath=remote_path + file_name)

    def _file_from_sftp(self, file_name):
        with self._sftp_connection() as sftp:
            remote_path = self.remote_path or ""
            if not self.remote_path or self.remote_path[-1] != "/":
                remote_path += "/"
            try:
                output_buffer = BytesIO()
                sftp.getfo(remote_path + file_name, output_buffer)
                file = base64.b64encode(output_buffer.getvalue())
            except Exception:
                exceptions.UserError(
                    _("An error ocurred when trying to import file: %s") % Exception
                )
            return file

    def _sftp_delete_file(self, file_name):
        with self._sftp_connection() as sftp:
            remote_path = self.remote_path or ""
            if not self.remote_path or self.remote_path[-1] != "/":
                remote_path += "/"
            sftp.remove(remote_path + file_name)

    def send_file_by_sftp(self, file, file_name):
        if not self.sftp_host or not self.sftp_user:
            return
        sftp_file_name = self.sftp_file_special_name or file_name
        self._file_to_sftp(sftp_file_name, file)

    def _sftp_get_names(self):
        file_names = []
        with self._sftp_connection() as sftp:
            remote_path = self.remote_path or ""
            if not self.remote_path or self.remote_path[-1] != "/":
                remote_path += "/"
            all_files = sftp.listdir(remote_path)
            for file in all_files:
                if file.startswith(self.sftp_file_special_name or ""):
                    file_names.append(file)
        return file_names

    # Email connection methods

    def _prepare_mail_values(self, file, file_name):
        return {
            "email_from": self.email_author.email,
            "recipient_ids": [(4, p.id) for p in self.destination_partner_ids],
            "subject": "Exportation of {}".format(file_name),
            "body_html": """
                <body>
                    <p>
                        This the data
                    </p>
                </body>
            """,
            "is_notification": False,
            "auto_delete": False,
            "attachment_ids": [(0, 0, {"name": file_name, "datas": file})],
        }

    def send_file_by_email(self, file, file_name):
        if not self.destination_partner_ids:
            return
        vals = self._prepare_mail_values(file, file_name)
        mail = self.env["mail.mail"].create(vals)
        mail.send()

    @api.model
    def _create_sequence(self, vals):
        seq_vals = {
            "name": "EDI Backend {}".format(vals["name"]),
            "code": "edi.backend",
            "padding": 4,
            "number_increment": 1,
        }
        if "company_id" in vals:
            seq_vals["company_id"] = vals["company_id"]
        return self.env["ir.sequence"].create(seq_vals)

    @api.model
    def create(self, vals):
        if not vals.get("sequence_id", False):
            vals["sequence_id"] = self._create_sequence(vals).id
        return super().create(vals)

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = (
            self.env["ir.model"]._get("edi.backend.communication.history").id
        )
        if self.id:
            values["alias_defaults"] = defaults = ast.literal_eval(
                self.alias_defaults or "{}"
            )
            defaults["edi_backend_id"] = self.id
        return values

    def action_import_history_run(self):
        records = self.env["edi.backend.communication.history"].search(
            [("edi_backend_id", "=", self.id)]
        )
        for record in records:
            if not record.applied_records:
                record.action_import_run()
        return


class EdiBackendCommunicationHistory(models.Model):
    _name = "edi.backend.communication.history"
    _description = "EDI Backend communication history"
    _rec_name = "create_date"
    _order = "create_date DESC"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    edi_backend_id = fields.Many2one(
        comodel_name="edi.backend",
        string="EDI Backend",
        required=True,
    )
    company_id = fields.Many2one(
        related="edi_backend_id.company_id",
        string="Company",
        store=True,
        readonly=True,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("not_sent", "Not sent"),
            ("sent", "Sent"),
            ("sent_errors", "Errors"),
            ("cancelled", "Cancelled"),
        ],
        string="Export state",
        default="not_sent",
        copy=False,
        help="Indicates the state of the Export send state",
    )
    model_name = fields.Char(
        related="edi_backend_id.model_id.model",
        readonly=True,
    )
    applied_domain = fields.Char()
    applied_records = fields.Char()
    applied_sequence = fields.Char()
    data = fields.Binary(string="Last File", attachment=True, readonly=True)
    file_name = fields.Char(string="File name")
    action_type = fields.Selection(related="edi_backend_id.action_type")
    active = fields.Boolean(default=True)
    notes = fields.Html()

    def get_applied_records(self):
        """
        Do a new search with all record ids due to an user can be delete a
        record so we can do not a browse aver this ids directly.
        """
        records = self.env[self.model_name].browse()
        if self.applied_records:
            record_ids = json.loads(self.applied_records)
            records = self.env[self.model_name].search([("id", "in", record_ids)])
        return records

    def action_set_no_send(self):
        records = self.get_applied_records()
        if records:
            getattr(
                records, "%s_action_backend_not_sent" % self.edi_backend_id.provider
            )()

    def action_rebuild_file(self):
        self.data = False
        self.edi_backend_id.action_export_run(history_line=self)

    def action_open_applied_records(self):
        records = self.get_applied_records()
        if records:
            action = {
                "type": "ir.actions.act_window",
                "view_mode": "tree,form",
                "name": _("Applied records (%(model_name)s)")
                % {"model_name": self.edi_backend_id.model_id.name},
                "res_model": self.model_name,
                "domain": [("id", "in", records.ids)],
            }
            return action

    def action_import_run(self):
        self.ensure_one()
        vals_list = self.edi_backend_id._get_vals_from_file(history=self)
        records = self.edi_backend_id._fill_data_from_vals(vals_list)
        self.applied_records = str(records)

    def message_new(self, msg_dict, custom_values=None):
        attachments = msg_dict.get("attachments", False)
        if attachments:
            if len(attachments) > 1:
                for i in range(1, len(attachments)):
                    cc_values = {
                        "data": base64.b64encode(attachments[i][1]),
                        "file_name": attachments[i][0],
                    }
                    cc_values.update(custom_values)
                    self.create(cc_values)
            cc_values = {
                "data": base64.b64encode(attachments[0][1]),
                "file_name": attachments[0][0],
            }
            cc_values.update(custom_values)
        return super().message_new(msg_dict, custom_values=cc_values)
