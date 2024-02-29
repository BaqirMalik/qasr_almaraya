# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class TicketReverse(models.TransientModel):
    _name = 'ticket.reverse'

    REFUND_TYPE_SELECTION = [('outbound', 'Outbound Ticket Only'), ('return', 'Return Ticket Only'), ('both', 'Both of Tickets')]

    ticket_id = fields.Many2one('airline.ticket')
    ticket_type = fields.Selection([('one_way', 'One Way'), ('two_way', 'Two Way'), ('open', 'Open')], required = True, default="one_way")
    vendor_currency_id = fields.Many2one(related="ticket_id.vendor_currency_id")
    currency_id = fields.Many2one(related="ticket_id.vendor_currency_id")
    vendor_refund_amount = fields.Monetary(currency_field='currency_id', required = True)
    customer_refund_amount = fields.Monetary(currency_field='currency_id', required = True)
    refund_type = fields.Selection(REFUND_TYPE_SELECTION, required = True, default='outbound')
    invoice_journal_id = fields.Many2one('account.journal')

    def action_refund(self):
        reversed_bill_id = self.ticket_id.create_reverse_bill()
        reversed_invoice_id = self.ticket_id.create_reverse_invoice()
        ticket_product_id = self.env.ref('airline_sc_automation.ticket')
        invoice_line = reversed_invoice_id.invoice_line_ids.filtered(lambda line: line.product_id.id == ticket_product_id.product_variant_id.id)
        bill_line = reversed_bill_id.invoice_line_ids.filtered(lambda line: line.product_id.id == ticket_product_id.product_variant_id.id)
        line_customer_refund_amount = self.customer_refund_amount / len(invoice_line)
        line_vendor_refund_amount = self.vendor_refund_amount / len(bill_line)

        if self.invoice_journal_id:
            reversed_invoice_id.journal_id = self.invoice_journal_id
        
        reversed_invoice_id.invoice_line_ids = [
            (1, line.id, {
                'price_unit': line_customer_refund_amount,
            }) for line in invoice_line
        ]

        reversed_bill_id.invoice_line_ids = [
            (1, line.id, {
                'price_unit': line_vendor_refund_amount,
            }) for line in bill_line
        ]
        reversed_bill_id.action_post()
        reversed_invoice_id.action_post()
        self.ticket_id.refund_line_ids.sudo().create({
            'ticket_id': self.ticket_id.id,
            'bill_id': reversed_bill_id.id,
            'invoice_id': reversed_invoice_id.id,
            'refund_type': self.refund_type,
        })

        invoice_refund_amount = sum(reversed_invoice_id.mapped('amount_total_signed'))
        bill_refund_amount = sum(reversed_bill_id.mapped('amount_total_signed'))
        price = self.ticket_id.main_price + invoice_refund_amount
        cost = self.ticket_id.main_cost - bill_refund_amount
        profit = price - cost
        user_ids = self.env.ref("airline_sc_automation.group_can_confirm_negative_profit_tickets").users.ids
        if profit < 0 and self.env.user.id not in user_ids:
            raise UserError("You cannot confirm a ticket with a negative profit.")


class TicketReverseConfirmed(models.TransientModel):
    _name = 'ticket.reverse.confirmed'

    REFUND_TYPE_SELECTION = [('outbound', 'Outbound Ticket Only'), ('return', 'Return Ticket Only'), ('both', 'Both of Tickets'), ('refund_before_payment', 'Refund Before Payment')]

    ticket_id = fields.Many2one('airline.ticket')
    ticket_type = fields.Selection([('one_way', 'One Way'), ('two_way', 'Two Way'), ('open', 'Open')], required = True, default="one_way")
    currency_id = fields.Many2one(related="ticket_id.vendor_currency_id")
    vendor_currency_id = fields.Many2one(related="ticket_id.vendor_currency_id")
    vendor_refund_amount = fields.Monetary(currency_field='currency_id', required = True)
    customer_refund_amount = fields.Monetary(currency_field='currency_id', required = True)
    refund_type = fields.Selection(REFUND_TYPE_SELECTION, required = True, default='refund_before_payment')
    
    def action_refund(self):

        reversed_bill_id = self.ticket_id.create_reverse_bill()
        reversed_invoice_id = self.ticket_id.create_reverse_invoice()
        ticket_product_id = self.env.ref('airline_sc_automation.ticket')
        bill_line = reversed_bill_id.invoice_line_ids.filtered(lambda line: line.product_id.id == ticket_product_id.product_variant_id.id)
        line_vendor_refund_amount = self.vendor_refund_amount / len(bill_line)
        invoice_line = reversed_invoice_id.invoice_line_ids.filtered(lambda line: line.product_id.id == ticket_product_id.product_variant_id.id)
        line_customer_refund_amount = self.customer_refund_amount / len(invoice_line)

        reversed_invoice_id.invoice_line_ids = [
                    (1, line.id, {
                        'price_unit': line_customer_refund_amount,
                    }) for line in invoice_line
                ]

        reversed_bill_id.invoice_line_ids = [
            (1, line.id, {
                'price_unit': line_vendor_refund_amount,
            }) for line in bill_line
        ]
        
        reversed_bill_id.action_post()
        reversed_invoice_id.action_post()
        self.ticket_id.refund_line_ids.sudo().create({
            'ticket_id': self.ticket_id.id,
            'bill_id': reversed_bill_id.id,
            'invoice_id': reversed_invoice_id.id,
            'refund_type': self.refund_type,
        })

        for pick in self.ticket_id.purchase_order_id.picking_ids:
            for move in pick.move_ids:
                scrap = self.env['stock.scrap'].create({
                    'product_id': move.product_id.id,
                    'scrap_qty': move.product_uom_qty,
                    'product_uom_id': move.product_uom.id,
                    'date_done': fields.Datetime.now()
                })
                scrap.do_scrap()

        invoice_refund_amount = sum(reversed_invoice_id.mapped('amount_total_signed'))
        bill_refund_amount = sum(reversed_bill_id.mapped('amount_total_signed'))
        price = self.ticket_id.main_price + invoice_refund_amount
        cost = self.ticket_id.main_cost - bill_refund_amount
        profit = price - cost
        user_ids = self.env.ref("airline_sc_automation.group_can_confirm_negative_profit_tickets").users.ids
        if profit < 0 and self.env.user.id not in user_ids:
            raise UserError("You cannot confirm a ticket with a negative profit.")
