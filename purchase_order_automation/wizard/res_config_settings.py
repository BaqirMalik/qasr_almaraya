from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    is_po_delivery_set_to_done = fields.Boolean("Is Purchase Delivery Set to Done", default=lambda self: self.env.user.company_id.is_po_delivery_set_to_done)
    create_invoice_for_po = fields.Boolean(string="Create Supplier Bill?", default=lambda self: self.env.user.company_id.create_invoice_for_po)
    validate_po_invoice = fields.Boolean(string='Validate Supplier Bills?', default=lambda self: self.env.user.company_id.validate_po_invoice)
    
    # create_invoice_for_po = fields.Boolean(related='company_id.create_invoice_for_po', string="Create Supplier Bill?")
    # validate_po_invoice = fields.Boolean(related='company_id.validate_po_invoice', string='Validate Supplier Bills?')

    
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            is_po_delivery_set_to_done=self.env.user.company_id.is_po_delivery_set_to_done,
            create_invoice_for_po = self.env.user.company_id.create_invoice_for_po,
            validate_po_invoice = self.env.user.company_id.validate_po_invoice,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        company_id=self.env.user.company_id
        company_id.is_po_delivery_set_to_done = self.is_po_delivery_set_to_done
        company_id.create_invoice_for_po = self.create_invoice_for_po 
        company_id.validate_po_invoice = self.validate_po_invoice


