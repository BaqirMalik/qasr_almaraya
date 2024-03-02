from odoo import api, fields, models, exceptions


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    def button_confirm(self):
        invoice_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            company_id = order.company_id
            if company_id.is_po_delivery_set_to_done and order.picking_ids: 
                for picking in self.picking_ids:
                    if picking.state == 'cancel':
                        continue
                    picking.action_assign()
                    picking.action_confirm()
                    for mv in picking.move_ids_without_package:
                        # mv.quantity_done = mv.product_uom_qty
                        mv.quantity = mv.product_uom_qty
                    picking.button_validate()

            if company_id.create_invoice_for_po and not order.invoice_ids:
                journal = journal_obj.search([('type', '=', 'purchase')],limit=1)
                
                invoice_id = invoice_obj.create({'purchase_id': order.id, 'partner_id':order.partner_id.id, 'move_type': 'in_invoice', 'journal_id': journal.id})
                
                invoice_id.purchase_id = order
                invoice_id.with_context(create_bill=True)._onchange_purchase_auto_complete()
                invoice_id._onchange_partner_id()
                invoice_id._onchange_quick_edit_line_ids()


                order.invoice_ids = invoice_id
                for line in order.invoice_ids.mapped('line_ids').filtered(lambda inv_line: inv_line.product_id.type == 'service' ):
                    line.with_context(check_move_validity = False).quantity = line.purchase_line_id.product_qty
            if company_id.validate_po_invoice and order.invoice_ids:
                for invoice in order.invoice_ids:
                    invoice.invoice_date = fields.Date.today()
                    try:
                        invoice.action_post()
                    except:
                        pass
            
        return res  
