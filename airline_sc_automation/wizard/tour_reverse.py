# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class TourReverse(models.TransientModel):
    _name = 'tour.reverse'


    tour_id = fields.Many2one('airline.tour')
    vendor_currency_id = fields.Many2one(related="tour_id.vendor_currency_id")
    currency_id = fields.Many2one(related="tour_id.currency_id")
    vendor_refund_amount = fields.Monetary(currency_field='vendor_currency_id', required = True)
    customer_refund_amount = fields.Monetary(currency_field='currency_id', required = True)
    invoice_journal_id = fields.Many2one('account.journal')

    def action_refund(self):
        reversed_bill_id = self.tour_id.create_reverse_bill()
        reversed_invoice_id = self.tour_id.create_reverse_invoice()
        tour_product_id = self.env.ref('airline_sc_automation.tour')
        invoice_line = reversed_invoice_id.invoice_line_ids.filtered(lambda line: line.product_id.id == tour_product_id.product_variant_id.id)
        bill_line = reversed_bill_id.invoice_line_ids.filtered(lambda line: line.product_id.id == tour_product_id.product_variant_id.id)
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
        self.tour_id.refund_line_ids.sudo().create({
            'tour_id': self.tour_id.id,
            'bill_id': reversed_bill_id.id,
            'invoice_id': reversed_invoice_id.id,
        })

        invoice_refund_amount = sum(reversed_invoice_id.mapped('amount_total_signed'))
        bill_refund_amount = sum(reversed_bill_id.mapped('amount_total_signed'))
        price = self.tour_id.main_price + invoice_refund_amount
        cost = self.tour_id.main_cost - bill_refund_amount
        profit = price - cost
        user_ids = self.env.ref("airline_sc_automation.group_can_confirm_negative_profit_tickets").users.ids
        if profit < 0 and self.env.user.id not in user_ids:
            raise UserError("You cannot confirm a ticket with a negative profit.")


class TourReverseConfirmed(models.TransientModel):
    _name = 'tour.reverse.confirmed'

    tour_id = fields.Many2one('airline.tour')
    vendor_currency_id = fields.Many2one(related="tour_id.vendor_currency_id")
    currency_id = fields.Many2one(related="tour_id.currency_id")
    vendor_refund_amount = fields.Monetary(currency_field='vendor_currency_id', required = True)
    customer_refund_amount = fields.Monetary(currency_field='currency_id', required = True)

    def action_refund(self):
        reversed_invoice_id = self.tour_id.create_reverse_invoice()
        reversed_bill_id = self.tour_id.create_reverse_bill()
        tour_product_id = self.env.ref('airline_sc_automation.tour')
        invoice_line = reversed_invoice_id.invoice_line_ids.filtered(lambda line: line.product_id.id == tour_product_id.product_variant_id.id)
        bill_line = reversed_bill_id.invoice_line_ids.filtered(lambda line: line.product_id.id == tour_product_id.product_variant_id.id)
        line_vendor_refund_amount = self.vendor_refund_amount / len(bill_line)
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
        self.tour_id.refund_line_ids.sudo().create({
            'tour_id': self.tour_id.id,
            'bill_id': reversed_bill_id.id,
            'invoice_id': reversed_invoice_id.id,
        })

        for pick in self.tour_id.purchase_order_id.picking_ids:
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
        price = self.tour_id.main_price + invoice_refund_amount
        cost = self.tour_id.main_cost - bill_refund_amount
        profit = price - cost
        user_ids = self.env.ref("airline_sc_automation.group_can_confirm_negative_profit_tickets").users.ids
        if profit < 0 and self.env.user.id not in user_ids:
            raise UserError("You cannot confirm a ticket with a negative profit.")