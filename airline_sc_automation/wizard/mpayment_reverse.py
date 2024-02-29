# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class MpaymentReverse(models.TransientModel):
    _name = 'mpayment.reverse'


    mpayment_id = fields.Many2one('airline.mpayment')
    vendor_currency_id = fields.Many2one(related="mpayment_id.vendor_currency_id")
    currency_id = fields.Many2one(related="mpayment_id.currency_id")
    vendor_refund_amount = fields.Monetary(currency_field='vendor_currency_id', required = True)
    customer_refund_amount = fields.Monetary(currency_field='currency_id', required = True)
    invoice_journal_id = fields.Many2one('account.journal')

    def action_refund(self):
        reversed_bill_id = self.mpayment_id.create_reverse_bill()
        reversed_invoice_id = self.mpayment_id.create_reverse_invoice()
        mpayment_product_id = self.env.ref('airline_sc_automation.mpayment')
        invoice_line = reversed_invoice_id.invoice_line_ids.filtered(lambda line: line.product_id.id == mpayment_product_id.product_variant_id.id)
        bill_line = reversed_bill_id.invoice_line_ids.filtered(lambda line: line.product_id.id == mpayment_product_id.product_variant_id.id)
        
        if self.invoice_journal_id:
            reversed_invoice_id.journal_id = self.invoice_journal_id
        reversed_invoice_id.invoice_line_ids = [
            (1, invoice_line.id, {
                'price_unit': self.customer_refund_amount,
            }),
        ]
        reversed_bill_id.invoice_line_ids = [
            (1, bill_line.id, {
                'price_unit': self.vendor_refund_amount,
            }),
        ]
        reversed_bill_id.action_post()
        reversed_invoice_id.action_post()
        self.mpayment_id.refund_line_ids.sudo().create({
            'mpayment_id': self.mpayment_id.id,
            'bill_id': reversed_bill_id.id,
            'invoice_id': reversed_invoice_id.id,
        })
        invoice_refund_amount = sum(reversed_invoice_id.mapped('amount_total_signed'))
        bill_refund_amount = sum(reversed_bill_id.mapped('amount_total_signed'))
        price = self.mpayment_id.main_price + invoice_refund_amount
        cost = self.mpayment_id.main_cost - bill_refund_amount
        profit = price - cost
        user_ids = self.env.ref("airline_sc_automation.group_can_confirm_negative_profit_tickets").users.ids
        if profit < 0 and self.env.user.id not in user_ids:
            raise UserError("You cannot confirm a Mpayment with a negative profit.")

class MPaymentReverseConfirmed(models.TransientModel):
    _name = 'mpayment.reverse.confirmed'


    mpayment_id = fields.Many2one('airline.mpayment')
    vendor_currency_id = fields.Many2one(related="mpayment_id.vendor_currency_id")
    currency_id = fields.Many2one(related="mpayment_id.currency_id")
    vendor_refund_amount = fields.Monetary(currency_field='vendor_currency_id', required = True)
    customer_refund_amount = fields.Monetary(currency_field='currency_id', required = True)

    def action_refund(self):
        reversed_invoice_id = self.mpayment_id.create_reverse_invoice()
        reversed_bill_id = self.mpayment_id.create_reverse_bill()
        mpayment_product_id = self.env.ref('airline_sc_automation.mpayment')
        bill_line = reversed_bill_id.invoice_line_ids.filtered(lambda line: line.product_id.id == mpayment_product_id.product_variant_id.id)
        invoice_line = reversed_invoice_id.invoice_line_ids.filtered(lambda line: line.product_id.id == mpayment_product_id.product_variant_id.id)

        reversed_invoice_id.invoice_line_ids = [
                (1, invoice_line.id, {
                    'price_unit': self.customer_refund_amount,
                })
            ]
        reversed_bill_id.invoice_line_ids = [
            (1, bill_line.id, {
                'price_unit': self.vendor_refund_amount,
            }),
        ]

        reversed_bill_id.action_post()
        reversed_invoice_id.action_post()
        self.mpayment_id.refund_line_ids.sudo().create({
            'mpayment_id': self.mpayment_id.id,
            'bill_id': reversed_bill_id.id,
            'invoice_id': reversed_invoice_id.id,
        })

        for pick in self.mpayment_id.purchase_order_id.picking_ids:
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
        price = self.mpayment_id.main_price + invoice_refund_amount
        cost = self.mpayment_id.main_cost - bill_refund_amount
        profit = price - cost
        user_ids = self.env.ref("airline_sc_automation.group_can_confirm_negative_profit_tickets").users.ids
        if profit < 0 and self.env.user.id not in user_ids:
            raise UserError("You cannot confirm a Mpayment with a negative profit.")
        
