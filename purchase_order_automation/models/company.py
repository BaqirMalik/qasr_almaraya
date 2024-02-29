from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    is_po_delivery_set_to_done = fields.Boolean(string="Is Purchase Delivery Set to Done")
    create_invoice_for_po=fields.Boolean(string='Create Supplier Bill?')
    validate_po_invoice = fields.Boolean(string='Validate Supplier Bills?')
