# -*- coding: utf-8 -*-

from odoo import models, fields, api
import pytz
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class AirlineVisa(models.Model):
    _name = 'airline.visa'
    _description = "Visa"
    _inherit = ['mail.thread']


    STATE_SELECTION = [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('canceled', 'Canceled')]
    
    state = fields.Selection(STATE_SELECTION, default="draft", track_visibility='always')
    name = fields.Char(string="name", required=True, copy=False, readonly=True, index=True, default='New')
    activity_ids = fields.One2many('mail.activity', 'res_id', string='Activities', domain=[('res_model', '=', 'airline.visa')])
    vendor_id = fields.Many2one('res.partner', required = True, track_visibility='always', domain=[('is_visa_vendor', '=', True)])
    customer_id = fields.Many2one('res.partner', required = True, track_visibility='always')
    mobile = fields.Char(related='customer_id.phone')
    email = fields.Char(related='customer_id.email')
    passport_number = fields.Char(related='customer_id.id_number')
    cost = fields.Monetary(currency_field='vendor_currency_id', compute="_compute_cost_price")
    price = fields.Monetary(currency_field='currency_id', compute="_compute_cost_price")
    currency_id = fields.Many2one('res.currency', default = lambda self: self._get_vendor_currency(), readonly=True, track_visibility='always')
    vendor_currency_id = fields.Many2one('res.currency', default = lambda self: self._get_vendor_currency(), readonly=True, track_visibility='always')
    issue_date_note = fields.Char()
    issue_date_from = fields.Datetime(required = True, track_visibility='always')
    issue_date_to = fields.Datetime(required = True, track_visibility='always')
    issue_range_from = fields.Integer(required = True)
    issue_range_to = fields.Integer(required = True)
    country_id = fields.Many2one('airline.visa.country')
    type_id = fields.Many2one('airline.visa.type')
    needed_documents = fields.Char()
    description = fields.Html()
    notes = fields.Text()
    passenger_ids = fields.One2many('visa.passenger.line', 'visa_id')
    offer_line_id = fields.Many2one('airline.visa.offer')
    residence_duration_id = fields.Many2one('visa.residence.duration')
    visa_validity_id = fields.Many2one('visa.validity')
    has_refund = fields.Boolean(compute="_compute_has_refund")
    sale_order_id = fields.Many2one('sale.order')
    purchase_order_id = fields.Many2one('purchase.order')
    bill_id = fields.Many2one('account.move', compute = "_compute_bill_id", store=True)
    invoice_id = fields.Many2one('account.move', compute = "_compute_invoice_id", store=True)
    invoice_state = fields.Selection(related='invoice_id.state')
    invoice_payment_state = fields.Selection(related='invoice_id.payment_state')
    invoice_move_type = fields.Selection(related="invoice_id.move_type")
    invoice_amount_residual = fields.Monetary(related="invoice_id.amount_residual")
    refund_line_ids = fields.One2many('visa.refund.line', 'visa_id')
    readonly_customer = fields.Boolean()
    passenger_names = fields.Char(compute="_compute_passenger_names", store=True)
    company_currency_id = fields.Many2one('res.currency', string='Company', compute="_compute_company_currency")
    profit = fields.Float(currency_field='company_currency_id', compute="_compute_profit")
    main_cost = fields.Monetary(currency_field='company_currency_id', compute="_compute_main_cost_price")
    main_price = fields.Monetary(currency_field='company_currency_id', compute="_compute_main_price_price")
    bill_state = fields.Selection(related='bill_id.state')
    invoice_state = fields.Selection(related='invoice_id.state')
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
                return
            for move in rec.sale_order_id.invoice_ids:
                if  move.state == 'cancel':
                    rec.main_cost = 0
                    rec.is_line_red = True
                    return
            rec.is_line_red = False
            # rec.main_cost = rec.vendor_currency_id.with_context(date = rec.create_date).compute(rec.cost, self.env.company.currency_id)
            date = rec.create_date or fields.Date.today()
            rec.main_cost = rec.currency_id._convert(
                rec.cost, self.env.company.currency_id, self.env.company, date)
    def _compute_main_price_price(self):
        for rec in self:
            if rec.sale_order_id.state == 'cancel' or rec.state == 'canceled':
                rec.main_price = 0
                return
            for move in rec.sale_order_id.invoice_ids:
                if  move.state == 'cancel':
                    rec.main_price = 0
                    return
            # rec.main_price = rec.currency_id.with_context(date = rec.create_date).compute(rec.price, self.env.company.currency_id)
            date = rec.create_date or fields.Date.today()
            rec.main_price = rec.currency_id._convert(
                rec.price, self.env.company.currency_id, self.env.company, date)
    def _compute_profit(self):
        for rec in self:
            rec.profit = rec.main_price - rec.main_cost

    def _compute_profit(self):
        for rec in self:
            if rec.sale_order_id.state == 'cancel' or rec.state == 'canceled':
                rec.profit = 0
                return
            for move in rec.sale_order_id.invoice_ids:
                if  move.state == 'cancel':
                    rec.profit = 0
                    return
            # main_currency_price = rec.currency_id.with_context(date = rec.create_date).compute(rec.price, self.env.company.currency_id)
            # main_currency_cost = rec.vendor_currency_id.with_context(date = rec.create_date).compute(rec.cost, self.env.company.currency_id)

            date = rec.create_date or fields.Date.today()
            main_currency_price = rec.currency_id._convert(
                rec.price, self.env.company.currency_id, self.env.company, date)

            main_currency_cost = rec.currency_id._convert(
                rec.cost, self.env.company.currency_id, self.env.company, date)



            invoice_refund_amount = sum(rec.refund_line_ids.invoice_id.mapped('amount_total_signed'))
            bill_refund_amount = sum(rec.refund_line_ids.bill_id.mapped('amount_total_signed'))
            price = main_currency_price + invoice_refund_amount
            cost = main_currency_cost - bill_refund_amount
            rec.profit = price - cost
    
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

    @api.onchange('issue_range_from')
    def onchange_issue_range_from(self):
        self.issue_date_from = fields.Datetime.now() + timedelta(days = self.issue_range_from)
    

    @api.onchange('issue_range_to')
    def onchange_issue_range_to(self):
        self.issue_date_to = fields.Datetime.now() + timedelta(days = self.issue_range_to)


    def _get_vendor_currency(self):
        return self.vendor_id.airline_currency_id
    

    @api.onchange('vendor_id')
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

    @api.constrains('state')
    def _compute_invoice_id(self):
        for rec in self:
            if rec.sale_order_id:
                # rec.invoice_id = self.sale_order_id.invoice_ids.filtered(lambda self: self.state == 'posted')[0]
                rec.invoice_id = self.sale_order_id.invoice_ids.filtered(lambda self: self.state == 'posted')
            else:
                rec.invoice_id = False

    # @api.constrains('state')
    # def _compute_bill_id(self):
    #     for rec in self:
    #         if rec.sale_order_id:
    #             rec.bill_id = self.purchase_order_id.invoice_ids.filtered(lambda self: self.state == 'posted')[0]
    #         else:
    #             rec.bill_id = False

    @api.constrains('state')
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



    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('airline.visa.code')
        res = super(AirlineVisa, self).create(values)
        return res
    
    

    def _prepare_order_lines(self, type):
        product_id = self.env.ref('airline_sc_automation.visa').product_variant_id
        visa_lines = []
        for line in self.passenger_ids:
            price_unit = line.price if type == 'sale' else line.cost
            visa_line = (0, 0, {
                'product_id': product_id.id,
                'name': f"{line.passenger_id.name} - {line.passenger_type.code}",
                'price_unit': price_unit,
            })
            if type == 'sale':
                visa_line[2]['product_uom_qty'] = 1
            elif type == 'purchase':
                visa_line[2]['product_qty'] = 1
            visa_lines.append(visa_line)
        return visa_lines



    def validate_passenger_lines(self):
        if len(self.passenger_ids) == 0:
            raise UserError("Please add passengers before confirming the visa.")

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


    def action_cancel(self):
        self.state = 'canceled'


    def action_draft(self):
        self.state = 'draft'


    def action_register_payment(self):
        return self.invoice_id.action_register_payment()

    def action_reverse(self):
        return {
            'name': f'Refund {self.name}',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'visa.reverse',
            'target': 'new',
            'context': {
                'default_visa_id': self.id,
            },
        }
        
    def action_reverse_confirmed(self):
        return {
            'name': f'Refund {self.name}',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'visa.reverse.confirmed',
            'target': 'new',
            'context': {
                'default_visa_id': self.id,
            },
        }

    def create_activity(self):
        user_id = self.env.user
        tz = pytz.timezone(user_id.tz or 'UTC')
        utc_offset = tz.utcoffset(datetime.utcnow()).total_seconds() // 3600
        assignee_id = self.assignee_id.id if self.assignee_id else self.env.user.id
        mail_activity_return = {
            'res_id': self.id,
            'res_model_id': self.env.ref('airline_sc_automation.model_airline_visa').id,
            'user_id': assignee_id,
            'summary': f'{self.name} Visa Issue deadline',
            'note': f'Check the status of the Visa for {self.customer_id.name}. Today is the issue deadline.',
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'date_deadline': self.issue_date_to + timedelta(hours=utc_offset),
        }
        self.env['mail.activity'].create(mail_activity_return)


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
    


    def create_reverse_bill(self):
        res = self.env['account.move.reversal'].create({
            'residual': self.bill_id.amount_residual,
            'company_id': self.bill_id.company_id.id,
            'move_ids': [(6, 0, [self.bill_id.id])],
            'available_journal_ids': self.bill_id.suitable_journal_ids.ids,
            'journal_id': self.bill_id.journal_id.id,
            'refund_method': 'refund',
            'date': fields.Date.today(),
            'currency_id': self.vendor_currency_id.id,
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

    


class PassengerLine(models.Model):
    _name = "visa.passenger.line"

    
    visa_id = fields.Many2one('airline.visa')
    passenger_id = fields.Many2one('res.partner')
    mobile = fields.Char(related='passenger_id.phone')
    email = fields.Char(related='passenger_id.email')
    passenger_type = fields.Many2one('passenger.type')
    state = fields.Selection(related="visa_id.state")
    sequence = fields.Integer()
    currency_id = fields.Many2one(related="visa_id.currency_id")
    vendor_id = fields.Many2one(related="visa_id.vendor_id")
    vendor_currency_id = fields.Many2one(related="visa_id.vendor_currency_id")
    cost = fields.Monetary(currency_field='vendor_currency_id', required = True, track_visibility='always')
    price = fields.Monetary(currency_field='currency_id', required = True, track_visibility='always')


    def duplicate_line(self):
        self.copy(default={'passenger_id': False})

            



class VisaCountry(models.Model):
    _name = "airline.visa.country"

    name = fields.Char()

    residence_duration_ids = fields.Many2many('visa.residence.duration')
    visa_validity_ids = fields.Many2many('visa.validity')
    visa_type_ids = fields.Many2many('airline.visa.type')


class VisaType(models.Model):
    _name = "airline.visa.type"

    name = fields.Char()
    country_ids = fields.Many2many('airline.visa.country')



class VisaResidenceDuration(models.Model):
    _name = "visa.residence.duration"

    name = fields.Char()
    country_ids = fields.Many2many('airline.visa.country')


class VisaValidity(models.Model):
    _name = "visa.validity"

    name = fields.Char()
    country_ids = fields.Many2many('airline.visa.country')



class VisaRefundLine(models.Model):
    _name = "visa.refund.line"
    _description = "Refund Line"


    visa_id = fields.Many2one('airline.visa')
    bill_id = fields.Many2one('account.move')
    invoice_id = fields.Many2one('account.move')
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
    


class VisaOffer(models.Model):
    _name = "airline.visa.offer"

    country_id = fields.Many2one('airline.visa.country')
    type_id = fields.Many2one('airline.visa.type')
    vendor_id = fields.Many2one('res.partner', required = True, track_visibility='always', domain=[('is_visa_vendor', '=', True)])
    residence_duration_id = fields.Many2one('visa.residence.duration')
    validity_id = fields.Many2one('visa.validity')
    cost = fields.Monetary(currency_field='vendor_currency_id', required = True, track_visibility='always')
    vendor_currency_id = fields.Many2one(related="vendor_id.airline_currency_id")
    price = fields.Monetary(currency_field='currency_id', required = True, track_visibility='always')
    currency_id = fields.Many2one('res.currency', default = lambda self: self.env.user.company_id.currency_id.id, readonly=True, track_visibility='always')
    child_price = fields.Monetary()
    issue_date_note = fields.Char()
    notes = fields.Char()



    def action_create_visa(self):
        return {
            'name': f'New Visa for {self.country_id.name} by {self.vendor_id.name}',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'airline.visa',
            'context': {
                'default_offer_line_id': self.id,
                'default_vendor_id': self.vendor_id.id,
                'default_country_id': self.country_id.id,
                'default_residence_duration_id': self.residence_duration_id.id,
                'default_visa_validity_id': self.validity_id.id,
                'default_cost': self.cost,
                'default_price': self.price,
                'default_issue_date_note': self.issue_date_note,
                'default_notes': self.notes,
            },
        }