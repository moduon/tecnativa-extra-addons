# Copyright 2020 Tecnativa - Carlos Dauden
# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tests import Form


class Agreement(models.Model):
    _inherit = "agreement"

    mef_lot_id = fields.Many2one(
        comodel_name="stock.production.lot",
        string="Serial number",
        domain=[("product_id.categ_id.is_unilever_mef", "=", "True")],
    )
    mef_product_standard_price = fields.Float(
        string="Product cost",
        digits="Product Price",
        compute="_compute_mef_product_standard_price",
        store=True,
        readonly=False,
        copy=False,
    )
    mef_product_categ_id = fields.Many2one(
        comodel_name="product.category",
        related="mef_lot_id.product_id.categ_id",
        string="Product category",
    )
    mef_product_id = fields.Many2one(
        comodel_name="product.product",
        related="mef_lot_id.product_id",
        string="Product",
    )
    mef_supplier_contact_id = fields.Many2one(
        comodel_name="res.partner",
        string="Supplier contact",
    )
    mef_supplier_id = fields.Many2one(
        comodel_name="res.partner",
        related="mef_supplier_contact_id.commercial_partner_id",
        string="Supplier",
    )
    mef_owner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Owner",
    )
    mef_returned_code = fields.Char(
        string="Returned code",
        copy=False,
    )
    mef_returned_date = fields.Date(
        string="Returned date",
        copy=False,
    )
    mef_returned_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        copy=False,
        readonly=True,
    )
    mef_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        copy=False,
        readonly=True,
    )
    code = fields.Char(compute="_compute_code", store=True, readonly=False)

    @api.depends("mef_lot_id")
    def _compute_mef_product_standard_price(self):
        for agreement in self:
            agreement.mef_product_standard_price = (
                agreement.mef_lot_id.product_id.standard_price
            )

    @api.depends("domain")
    def _compute_code(self):
        for agreement in self:
            if agreement.domain == "unilever_mef" and not agreement.code:
                agreement.code = "/"

    @api.model
    def _domain_selection(self):
        res = super()._domain_selection()
        res.append(("unilever_mef", _("Unilever MEF")))
        return res

    @api.model
    def create(self, vals):
        if vals.get("domain") == "unilever_mef" and vals.get("code", "/") == "/":
            vals["code"] = (
                self.env["ir.sequence"].next_by_code("agreement.unilever_mef.out")
                or "/"
            )
        return super().create(vals)

    def assign_return_code(self):
        IrSequence = self.env["ir.sequence"]
        for agreement in self:
            vals = {
                "mef_returned_code": IrSequence.next_by_code(
                    "agreement.unilever_mef.out"
                ),
                "mef_returned_date": fields.Date.today(),
            }
            agreement.write(vals)

    def copy(self, default=None):
        """Set by default / to be assigned a sequence"""
        if self.domain != "unilever_mef":
            return super().copy(default=default)
        default.setdefault("code", "/")
        return super().copy(default)

    def create_procurement(self):
        return self.env["procurement.group"].create({"name": f"MEF-{self.code}"})

    def action_delivery_fresh_asset(self):
        """
        Create an internal picking with a special picking type operation.
        Not take in account multi warehouse until user request it.
        """
        self.ensure_one()
        if self.mef_picking_id and self.mef_picking_id.state != "cancel":
            return self.action_view_delivery()
        StockMove = self.env["stock.move"]
        picking_type = self.env.ref("agreement_unilever_mef.fresh_asset_picking_type")
        location_customer = self.env.ref("stock.stock_location_customers")
        location_stock = self.env.ref("stock.stock_location_stock")
        move = StockMove.create(
            {
                "name": f"MEF: {self.code} - {self.mef_product_id.name}",
                "origin": f"MEF: {self.code}",
                "partner_id": self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": location_stock.id,
                "location_dest_id": location_customer.id,
                "product_id": self.mef_product_id.id,
                "product_uom_qty": 1.0,
                "product_uom": self.mef_product_id.uom_id.id,
                "group_id": self.create_procurement().id,
            }
        )
        move.with_context(force_lot_fresh_asset=self.mef_lot_id)._action_confirm()
        move._action_assign()
        self.mef_picking_id = move.picking_id.id

    def get_return_picking_wizard(self, picking):
        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking.ids,
                active_id=picking.ids[0],
                active_model="stock.picking",
            )
        )
        return stock_return_picking_form.save()

    def action_return_fresh_asset(self):
        """
        Create an internal picking with a special picking type operation
        """
        self.ensure_one()
        self.assign_return_code()
        if not self.mef_picking_id or self.mef_picking_id.state != "done":
            raise UserError(
                _("You cannot return an asset " "until you have delivered one first")
            )
        return_moves = self.mef_picking_id.mapped(
            "move_lines.returned_move_ids"
        ).filtered(lambda m: m.state != "cancel")
        if return_moves:
            return self.action_view_delivery(pickings=return_moves.mapped("picking_id"))
        # Make a return from delivered picking
        wizard = self.get_return_picking_wizard(self.mef_picking_id)
        wiz_lines = wizard.product_return_moves.filtered(
            lambda rm: rm.product_id != self.mef_product_id
        )
        wiz_lines.unlink()
        wizard.product_return_moves.write({"quantity": 1.0})
        new_picking_id, pick_type_id = wizard.with_context(
            force_lot_fresh_asset=self.mef_lot_id
        )._create_returns()
        self.mef_returned_picking_id = new_picking_id
        self.end_date = fields.Date.today()

    def action_view_delivery(self, data=False, pickings=False):
        """
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        """
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "stock.action_picking_tree_all"
        )
        if not pickings:
            pickings = self.env["stock.picking"].browse()
        pickings += self.mef_picking_id + self.mef_returned_picking_id
        if len(pickings) > 1:
            action["domain"] = [("id", "in", pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref("stock.view_picking_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = pickings.id
        return action
