# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import pytz
from datetime import datetime, timedelta

class AirlineTicket(models.Model):
    _name = 'airline.ticket'
    _description = 'Airline Ticket'
    _inherit = ['mail.thread']

    STATE_SELECTION = [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('canceled', 'Canceled')]
    
    activity_ids = fields.One2many('mail.activity', 'res_id', string='Activities', domain=[('res_model', '=', 'airline.ticket')])
    name = fields.Char(string="name", required=True, copy=False, readonly=True, index=True, default='New')
    state = fields.Selection(STATE_SELECTION, default="draft", track_visibility='always')
    pnr = fields.Char(string="PNR", required = True, track_visibility='always')
    vendor_id = fields.Many2one('res.partner', required = True, track_visibility='always')
    customer_id = fields.Many2one('res.partner', required = True, track_visibility='always')
    flight_number = fields.Char(track_visibility='always')
    return_flight_number = fields.Char(track_visibility='always')
    ticket_type = fields.Selection([('one_way', 'One Way'), ('two_way', 'Two Way'), ('open', 'Open')], required = True, default="one_way")
    source_id = fields.Many2one('ticket.destination', required = True, track_visibility='always')
    destination_id = fields.Many2one('ticket.destination', required = True, track_visibility='always')
    currency_id = fields.Many2one('res.currency', default = lambda self: self._get_vendor_currency(), readonly=True, track_visibility='always')
    vendor_currency_id = fields.Many2one('res.currency', default = lambda self: self._get_vendor_currency(), readonly=True, track_visibility='always')
    cost = fields.Monetary(currency_field='vendor_currency_id', compute="_compute_cost_price")
    price = fields.Monetary(currency_field='currency_id', compute="_compute_cost_price")
    mobile = fields.Char(related='customer_id.phone')
    email = fields.Char(related='customer_id.email')
    first_flight_date = fields.Datetime(required = True, track_visibility='always')
    second_flight_date = fields.Datetime(track_visibility='always')
    passenger_ids = fields.One2many('passenger.line', 'ticket_id')
    readonly_customer = fields.Boolean(default = False)
    sale_order_id = fields.Many2one('sale.order')
    purchase_order_id = fields.Many2one('purchase.order')
    bill_id = fields.Many2one('account.move', compute = "_compute_bill_id", store=True)
    invoice_id = fields.Many2one('account.move', compute = "_compute_invoice_id", store=True)
    invoice_state = fields.Selection(related='invoice_id.state')
    invoice_payment_state = fields.Selection(related='invoice_id.payment_state')
    invoice_move_type = fields.Selection(related="invoice_id.move_type")
    invoice_amount_residual = fields.Monetary(related="invoice_id.amount_residual")
    refund_line_ids = fields.One2many('ticket.refund.line', 'ticket_id')
    has_refund = fields.Boolean(compute="_compute_has_refund")
    ticket_numbers = fields.Char(compute="_compute_ticket_numbers", store=True)
    passenger_names = fields.Char(compute="_compute_passenger_names", store=True)
    company_currency_id = fields.Many2one('res.currency', string='Company', compute="_compute_company_currency")
    profit = fields.Float(currency_field='company_currency_id', compute="_compute_profit")
    main_cost = fields.Monetary(currency_field='company_currency_id', compute="_compute_main_cost_price")
    main_price = fields.Monetary(currency_field='company_currency_id', compute="_compute_main_price_price")
    bill_state = fields.Selection(related='bill_id.state')
    invoice_state = fields.Selection(related='invoice_id.state')
    is_invoice_paid = fields.Boolean("Is Invoice Paid", default=False)
    is_line_red = fields.Boolean(compute="_compute_main_cost_price")
    assignee_id = fields.Many2one('res.users')

    def _compute_company_currency(self):
        for rec in self:
            rec.company_currency_id = rec.env.company.currency_id.id

    def _compute_main_cost_price(self):
        for rec in self:
            if rec.sale_order_id.state == 'cancel' or rec.state == 'canceled':
                rec.main_cost = 0
                rec.is_line_red = True
                # return
            for move in rec.sale_order_id.invoice_ids:
                if move.state == 'cancel':
                    rec.main_cost = 0
                    rec.is_line_red = True
                    # return
            rec.is_line_red = False
            # rec.main_cost = rec.vendor_currency_id.with_context(date = rec.create_date).compute(rec.cost, self.env.company.currency_id)
            date = rec.create_date or fields.Date.today()
            rec.main_cost = rec.currency_id._convert(
                rec.cost, self.env.company.currency_id, self.env.company, date)
    def _compute_main_price_price(self):
        for rec in self:
            if rec.sale_order_id.state == 'cancel' or rec.state == 'canceled':
                rec.main_price = 0
                # return
            for move in rec.sale_order_id.invoice_ids:
                if  move.state == 'cancel':
                    rec.main_price = 0
                    # return
            date = rec.create_date or fields.Date.today()
            # rec.main_price = rec.currency_id.with_context(date = rec.create_date).compute(rec.price, self.env.company.currency_id)
            rec.main_price = rec.currency_id._convert(
                rec.price,self.env.company.currency_id,self.env.company,date)
    def _compute_profit(self):
        for rec in self:
            if rec.sale_order_id.state == 'cancel' or rec.state == 'canceled':
                rec.profit = 0
                # return
            for move in rec.sale_order_id.invoice_ids:
                if  move.state == 'cancel':
                    rec.profit = 0
                    # return
            invoice_refund_amount = sum(rec.refund_line_ids.invoice_id.mapped('amount_total_signed'))
            bill_refund_amount = sum(rec.refund_line_ids.bill_id.mapped('amount_total_signed'))
            price = rec.main_price + invoice_refund_amount
            cost = rec.main_cost - bill_refund_amount
            rec.profit = price - cost

    
    @api.constrains('passenger_ids')
    @api.onchange('passenger_ids')
    def _compute_ticket_numbers(self):
        for rec in self:
            rec.ticket_numbers = '.'.join(rec.passenger_ids.mapped(lambda self: self.ticket_number if self.ticket_number else ''))


    @api.constrains('passenger_ids')
    @api.onchange('passenger_ids')
    def _compute_passenger_names(self):
        for rec in self:
            rec.passenger_names = '.'.join(rec.passenger_ids.mapped(lambda self: self.passenger_id.name if self.passenger_id else ''))


    @api.onchange('passenger_ids')
    def _compute_cost_price(self):
        for rec in self:
            rec.cost = sum(rec.passenger_ids.mapped('cost'))
            rec.price = sum(rec.passenger_ids.mapped('price'))


    def _get_vendor_currency(self):
        return self.vendor_id.airline_currency_id
    

    @api.onchange('vendor_id', 'passenger_ids')
    def onchange_vendor_id(self):
        vendor_currency_id = self._get_vendor_currency()
        self.currency_id = vendor_currency_id
        self.vendor_currency_id = vendor_currency_id


    def _compute_has_refund(self):
        for rec in self:
            if rec.refund_line_ids.filtered(lambda line: line.invoice_state != 'cancel'):
                rec.has_refund = True
            else:
                rec.has_refund = False


    def action_reverse(self):
        return {
            'name': f'Refund {self.name}',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'ticket.reverse',
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_ticket_type': self.ticket_type,
            },
        }


    def create_reverse_bill(self):
        res = self.env['account.move.reversal'].create({
            'residual': self.bill_id.amount_residual,
            'company_id': self.bill_id.company_id.id,
            'move_ids': [(6, 0, [self.bill_id.id])],
            'available_journal_ids': self.bill_id.suitable_journal_ids.ids,
            'journal_id': self.bill_id.journal_id.id,
            # 'refund_method': 'refund',
            'move_type': 'refund',
            'date': fields.Date.today(),
        })
        res = res.reverse_moves()
        reversed_move = self.env['account.move'].browse(res.get('res_id'))
        reversed_move.move_type = 'in_refund'
        reversed_move.currency_id = self.vendor_currency_id.id
        return reversed_move
    
    def create_reverse_invoice(self):
        res = self.env['account.move.reversal'].create({
            'residual': self.invoice_id.amount_residual,
            'company_id': self.invoice_id.company_id.id,
            'move_ids': [(6, 0, [self.invoice_id.id])],
            'available_journal_ids': self.invoice_id.suitable_journal_ids.ids,
            'journal_id': self.invoice_id.journal_id.id,
            'date': fields.Date.today(),
            'currency_id': self.currency_id.id,
        })
        res = res.reverse_moves()
        reversed_move = self.env['account.move'].browse(res.get('res_id'))
        reversed_move.move_type = 'out_refund'
        reversed_move.currency_id = self.currency_id.id
        return reversed_move

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('airline.ticket.code')
        res = super(AirlineTicket, self).create(values)
        return res
    

    def _prepare_order_lines(self, type):
        product_id = self.env.ref('airline_sc_automation.ticket').product_variant_id
        ticket_lines = []
        for line in self.passenger_ids:
            price_unit = line.price if type == 'sale' else line.cost
            ticket_line = (0, 0, {
                'product_id': product_id.id,
                'name': f"{line.passenger_id.name} - {line.passenger_type.code} - {line.ticket_number}",
                'price_unit': price_unit,
            })
            if type == 'sale':
                ticket_line[2]['product_uom_qty'] = 1
            elif type == 'purchase':
                ticket_line[2]['product_qty'] = 1
            ticket_lines.append(ticket_line)
        return ticket_lines
    


    # @api.constrains('state')
    @api.constrains('sale_order_id')
    def _compute_invoice_id(self):
        for rec in self:
            if rec.sale_order_id:
                rec.invoice_id = self.sale_order_id.invoice_ids.filtered(lambda self: self.state == 'posted')
            else:
                rec.invoice_id = False

    @api.constrains('purchase_order_id')
    def _compute_bill_id(self):
        for rec in self:
            if rec.purchase_order_id:
                posted_invoices = rec.purchase_order_id.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                if posted_invoices:
                    rec.bill_id = posted_invoices[0]
                else:
                    rec.bill_id = False  # Set bill_id to False if no posted invoices found
            else:
                rec.bill_id = False  # Set bill_id to False if no purchase order id found

    # def action_register_payment(self):
    #     return self.invoice_id.action_register_payment()

    def action_register_payment(self):
        if self.sale_order_id:
            # try:
            #     self.invoice_id = self.sale_order_id.invoice_ids.filtered(lambda inv: inv.state == 'posted')[0]
            # except Exception:
            #     raise ValidationError("Create Invoice First From Sale Order"
            self.invoice_id = self.sale_order_id.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            invoice_id = self.sale_order_id._create_invoices()
            invoice_posted = invoice_id.action_post()
            self.invoice_id = invoice_id
        return invoice_id.action_register_payment()


    def validate_passenger_lines(self):
        if len(self.passenger_ids) == 0:
            raise UserError("Please add passengers before confirming the ticket.")
        for passenger_line in self.passenger_ids:
            if self.vendor_id.ticket_number_is_required and not all([passenger_line.passenger_id, passenger_line.ticket_number, passenger_line.passenger_type]):
                raise UserError("All Passengers Lines should have a Passenger, Ticket Number and Passenger Type.")
            elif not all([passenger_line.passenger_id, passenger_line.passenger_type]):
                raise UserError("All Passengers Lines should have a Passenger and Passenger Type.")

    def action_confirm(self):
        user_ids = self.env.ref("airline_sc_automation.group_can_confirm_negative_profit_tickets").users.ids
        if self.profit < 0 and self.env.user.id not in user_ids:
            raise UserError("You cannot confirm a ticket with a negative profit.")
        self.validate_passenger_lines()
        if not self.sale_order_id or not self.purchase_order_id:
            sales_price_list_id = self.env['product.pricelist'].search([('currency_id', '=', self.currency_id.id)])
            sale_order_vals = {
                'partner_id': self.customer_id.id,
                'date_order': fields.Date.today(),
                'order_line': self._prepare_order_lines('sale'),
            }
            if sales_price_list_id:
                sale_order_vals['pricelist_id'] = sales_price_list_id.id
            sale_order_id = self.env['sale.order'].create(sale_order_vals)
            if sale_order_id.state != 'draft':
                # If the sale order is not in draft state, raise an error
                raise ValueError("The sale order is not in draft state and cannot be confirmed.")


            purchase_order_id = self.env['purchase.order'].create({
                'partner_id': self.vendor_id.id,
                'date_order': fields.Date.today(),
                'order_line': self._prepare_order_lines('purchase'),
                'currency_id': self.vendor_currency_id.id,
            })
        else:
            sale_order_id = self.sale_order_id
            purchase_order_id = self.purchase_order_id
        sale_order_id.action_confirm()
        purchase_order_id.button_confirm()
        self.sale_order_id = sale_order_id.id
        self.purchase_order_id = purchase_order_id.id
        self.state = 'confirmed'
        self.create_activity()


    def create_activity(self):
        user_id = self.env.user
        tz = pytz.timezone(user_id.tz or 'UTC')
        utc_offset = tz.utcoffset(datetime.utcnow()).total_seconds() // 3600
        assignee_id = self.assignee_id.id if self.assignee_id else self.env.user.id
        mail_activity_departure = {
            'res_id': self.id,
            'res_model_id': self.env.ref('airline_sc_automation.model_airline_ticket').id,
            'user_id':  assignee_id,
            'summary': f'{self.name} Ticket Departure',
            'note': f"Contact {self.customer_id.name} and ask him about his flight.",
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'date_deadline': self.first_flight_date + timedelta(hours=utc_offset),
        }
        self.env['mail.activity'].create(mail_activity_departure)
        if self.ticket_type == 'two_way':
            mail_activity_return = {
                'res_id': self.id,
                'res_model_id': self.env.ref('airline_sc_automation.model_airline_ticket').id,
                'user_id': assignee_id,
                'summary': f'{self.name} Ticket Return',
                'note': f'Contact {self.customer_id.name} and ask him about his flight.',
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'date_deadline': self.second_flight_date + timedelta(hours=utc_offset),
            }
            self.env['mail.activity'].create(mail_activity_return)

    def action_cancel(self):
        self.state = 'canceled'

    def action_draft(self):
        self.state = 'draft'

    def action_reverse_confirmed(self):
        return {
                'name': f'Refund {self.name}',
                'view_mode': 'form',
                'type': 'ir.actions.act_window',
                'res_model': 'ticket.reverse.confirmed',
                'target': 'new',
                'context': {
                    'default_ticket_id': self.id,
                    'default_ticket_type': self.ticket_type,
                },
            }

    def open_sale_order(self):
        return {
            'name': f'Sale Order',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'views': [(self.env.ref('sale.view_order_form').id, 'form')],
            'target': 'current',
        }
    
    def open_purchase_order(self):
        return {
            'name': f'Purchase Order',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_order_id.id,
            'views': [(self.env.ref('purchase.purchase_order_form').id, 'form')],
            'target': 'current',
        }


class PassengerLine(models.Model):
    _name = "passenger.line"

    
    ticket_id = fields.Many2one('airline.ticket')
    passenger_id = fields.Many2one('res.partner')
    mobile = fields.Char(related='passenger_id.phone')
    email = fields.Char(related='passenger_id.email')
    ticket_number = fields.Char()
    passenger_type = fields.Many2one('passenger.type')
    state = fields.Selection(related="ticket_id.state")
    sequence = fields.Integer()
    currency_id = fields.Many2one(related="ticket_id.currency_id")
    vendor_id = fields.Many2one(related="ticket_id.vendor_id")
    ticket_number_is_required = fields.Boolean(related="vendor_id.ticket_number_is_required")
    vendor_currency_id = fields.Many2one(related="ticket_id.vendor_currency_id")
    cost = fields.Monetary(currency_field='vendor_currency_id', required = True, track_visibility='always')
    price = fields.Monetary(currency_field='currency_id', required = True, track_visibility='always')
    fare = fields.Monetary(currency_field='vendor_currency_id', track_visibility='always')
    tax = fields.Monetary(currency_field='vendor_currency_id', track_visibility='always')
    fee = fields.Monetary(currency_field='vendor_currency_id', track_visibility='always')
    customer_commission = fields.Float(track_visibility='always')
    vendor_commission = fields.Float(track_visibility='always')

    def duplicate_line(self):
        self.copy(default={'passenger_id': False, 'ticket_number': False})


    
    @api.onchange('fare', 'tax', 'fee', 'customer_commission', 'vendor_commission')
    def compute_cost_and_price(self):
        if not self.env.context.get('noonchange'):
            if not self.currency_id:
                raise UserError("Please select a vendor for the ticket before setting cost/price calculation fields.")
            self.env.context = self.with_context(noonchange=True).env.context
            self.cost  = self.fare + self.tax + self.fee - (self.fare * self.vendor_commission / 100)
            price = self.fare + self.tax + self.fee - (self.fare * self.customer_commission / 100)
            # self.price = self.vendor_currency_id.compute(price, self.currency_id)
            self.price = self.vendor_currency_id._convert(
                price, self.env.company.currency_id)

    @api.onchange('cost', 'price')
    def onchange_cost_price(self):
        if not self.env.context.get('noonchange'):
            self.env.context = self.with_context(noonchange=True).env.context
            self.fare = 0
            self.tax = 0
            self.fee = 0
            self.customer_commission = 0
            self.vendor_commission = 0
            

class PassengerType(models.Model):
    _name = "passenger.type"
    _rec_name = "code"

    name = fields.Char()
    code = fields.Char()


class TicketDestination(models.Model):
    _name = "ticket.destination"
    _description = "Destination"
    _rec_name = "code"

    name = fields.Char()
    code = fields.Char()



class TicketRefundLine(models.Model):
    _name = "ticket.refund.line"
    _description = "Refund Line"


    REFUND_TYPE_SELECTION = [('outbound', 'Outbound Ticket Only'), ('return', 'Return Ticket Only'), ('both', 'Both of Tickets'), ('refund_before_payment', 'Refund Before Payment')]

    ticket_id = fields.Many2one('airline.ticket')
    bill_id = fields.Many2one('account.move')
    invoice_id = fields.Many2one('account.move')
    refund_type = fields.Selection(REFUND_TYPE_SELECTION, required = True, default='outbound')
    invoice_state = fields.Selection(related='invoice_id.state', string='Invoice State')
    invoice_currency_id = fields.Many2one(related='invoice_id.currency_id')
    bill_currency_id = fields.Many2one(related='bill_id.currency_id')
    invoice_payment_state = fields.Selection(related='invoice_id.payment_state', string="Payment State")
    invoice_move_type = fields.Selection(related="invoice_id.move_type")
    invoice_amount_residual = fields.Monetary(related="invoice_id.amount_residual", currency_field='invoice_currency_id')
    invoice_amount_total = fields.Monetary(related="invoice_id.amount_total", currency_field='invoice_currency_id', string="Invoice Total")
    bill_amount_total = fields.Monetary(related="bill_id.amount_total", currency_field='bill_currency_id', string="Bill Total")



    def action_cancel(self):
        self.invoice_id.button_draft()
        self.invoice_id.button_cancel()
        self.bill_id.button_draft()
        self.bill_id.button_cancel()


    def action_register_payment(self):
        return self.invoice_id.action_register_payment()