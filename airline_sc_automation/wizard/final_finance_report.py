from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class FinalFinanceReport(models.TransientModel):
    _name = "finalfinance.report"
    _description = "finalfinance.report"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date", default=lambda self: fields.Date.today())
    show_results = fields.Boolean(string="Show Results")
    currency_id = fields.Many2one('res.currency', default = lambda self: self.env.ref('base.main_company').currency_id)
    iqd_currency_id = fields.Many2one('res.currency', default = lambda self: self.env.ref('base.IQD'))

    opening_balance_iqd = fields.Monetary(currency_field='iqd_currency_id')
    opening_balance_usd = fields.Monetary(currency_field='currency_id')
    ticket_profit = fields.Monetary(currency_field='currency_id')
    tour_profit = fields.Monetary(currency_field='currency_id')
    visa_profit = fields.Monetary(currency_field='currency_id')
    mpayment_profit = fields.Monetary(currency_field='currency_id')
    total_tickets_profit = fields.Monetary(currency_field='currency_id')
    total_expenses = fields.Monetary(currency_field='currency_id')
    net_profit = fields.Monetary(currency_field='currency_id')

    @api.onchange('date_end')
    def action_confirm(self):
        if not self.start_date:
            raise ValidationError(_('Please select a start date.'))
        elif not self.end_date:
            raise ValidationError(_('Please select an end date.'))
        elif self.start_date > self.end_date:
            raise ValidationError(_('Start date cannot be after the end date.'))
        
        self.ticket_profit = sum(self.env['airline.ticket'].search([('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date), ('state', '!=', 'canceled'),('invoice_id.state', '!=', 'cancel')]).mapped('profit'))
        self.tour_profit = sum(self.env['airline.tour'].search([('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date), ('state', '!=', 'canceled'),('invoice_id.state', '!=', 'cancel')]).mapped('profit'))
        self.visa_profit = sum(self.env['airline.visa'].search([('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date), ('state', '!=', 'canceled'),('invoice_id.state', '!=', 'cancel')]).mapped('profit'))
        self.mpayment_profit = sum(self.env['airline.mpayment'].search([('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date), ('state', '!=', 'canceled'),('invoice_id.state', '!=', 'cancel')]).mapped('profit'))
        self.total_tickets_profit = self.ticket_profit + self.tour_profit + self.visa_profit + self.mpayment_profit
        
        self.total_expenses = sum(self.env['account.move.line'].search([('date', '>=', self.start_date), ('date', '<=', self.end_date), ('account_id.is_expense_account', '=', True), ('move_id.state', '=', 'posted')]).mapped('balance'))
        self.opening_balance_iqd = sum(self.env['account.move.line'].search([('account_id.code', '=', '80888'), ('move_id.state', '=', 'posted')]).mapped('amount_currency'))
        self.opening_balance_usd = sum(self.env['account.move.line'].search([('account_id.code', '=', '88888'), ('move_id.state', '=', 'posted')]).mapped('balance'))
        self.net_profit = self.total_tickets_profit - self.total_expenses

        self.show_results = True
        return {
        'name': _('Final Finance Report'),
        'type': 'ir.actions.act_window',
        'res_model': 'finalfinance.report',
        'view_type': 'form',
        'view_mode': 'form',
        'res_id': self.id,
        'target': 'new',
    } 
            
