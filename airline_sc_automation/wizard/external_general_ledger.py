from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import datetime


class ExternalGeneralLedger(models.TransientModel):
    _name = "external.general.ledger"
    _description = "External General Ledger"

    date_from = fields.Date('Date From', required=True, default=datetime(datetime.now().year, 1, 1))
    date_to = fields.Date('Date To', required=True, default=fields.Date.today())
    account_ids = fields.Many2many('account.account', string='Accounts', required=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError(_('Date From must be before Date To'))


    def print_report_action(self):
        currency_ids = self.env['res.currency'].search([('active', '=', True)])
        currency_map = {}
        accounts_data = []

        for currency_id in currency_ids:
            for account_id in self.account_ids:
                currency_map[f"{account_id.id}-{currency_id.id}"] = {
                    'key': f'balance-{currency_id.id}',
                    'currency_id': currency_id, 
                    "current_balance": 0,
                    "init_balance": self.format_value(0, currency_id)
                }
                query = """
                    SELECT 
                        SUM(amount_currency) as init_balance
                    FROM 
                        account_move_line aml
                    JOIN 
                        account_move am ON aml.move_id = am.id
                    WHERE 
                        aml.account_id = %s 
                        AND aml.currency_id = %s
                        AND aml.date < %s 
                        AND am.state = 'posted' 
                """
                params = (account_id.id, currency_id.id, self.date_from)
                self.env.cr.execute(query, params)
                result = self.env.cr.fetchone()
                init_balance = result[0] if result and result[0] else 0
                currency_map[f"{account_id.id}-{currency_id.id}"]['current_balance'] = init_balance
                currency_map[f"{account_id.id}-{currency_id.id}"]['init_balance'] = self.format_value(init_balance, currency_id)


        for account_id in self.account_ids:
            account_data = {
                'id': str(account_id.id),
                'name': account_id.name,
                'moves': [],
            }
            move_lines = self.env['account.move.line'].search([
                ('account_id', '=', account_id.id), 
                ('date', '>=', self.date_from), 
                ('date', '<=', self.date_to), 
                ('move_id.state', '=', 'posted'), 
            ], order="date,id")
            for move_line in move_lines:
                currency_map[f"{account_id.id}-{move_line.currency_id.id}"]['current_balance'] += move_line.amount_currency
                move_data = {
                    'id': str(move_line.id),
                    'date': move_line.date,
                    'partner': move_line.partner_id.name if move_line.partner_id else '',
                    'debit': move_line.debit,
                    'credit': move_line.credit,
                    'communication': move_line.payment_id.ref if move_line.payment_id else '',
                    'amount_currency': self.format_value(move_line.amount_currency, move_line.currency_id)
                }
                for currency_id in currency_ids:
                    move_data[currency_map[f"{account_id.id}-{currency_id.id}"]['key']] = self.format_value(currency_map[f"{account_id.id}-{currency_id.id}"]["current_balance"], currency_id)
                account_data['moves'].append(move_data)
            accounts_data.append(account_data)

        totals_data = {}
        company_currency_id = self.env.company.currency_id
        for account_id in self.account_ids:
            account_total_balance = 0
            for currency_id in currency_ids:
                current_currency_balance = currency_map[f"{account_id.id}-{currency_id.id}"]['current_balance']
                account_total_balance += currency_id.with_context(date = self.date_to).compute(current_currency_balance, company_currency_id)
            totals_data[account_id.id] = self.format_value(account_total_balance, company_currency_id)
        report_data = {
            'date_to': self.date_to,
            'date_from': self.date_from,
            'currency_map': currency_map,
            'active_currency_ids': currency_ids.mapped(lambda currency_id: {'name': currency_id.name, 'key': f"balance-{currency_id.id}", 'id': str(currency_id.id), 'symbol': currency_id.symbol}),
            'data': accounts_data,
            'totals_data': totals_data,
        }
        return self.env.ref('airline_sc_automation.external_general_ledger_report_action').report_action(self, data=report_data) 


    def format_value(self, value, currency_id, figure_type='monetary', blank_if_zero=False):
        report = self.env['account.report']
        return {
            'value': report.format_value(value, currency_id, figure_type=figure_type, blank_if_zero=blank_if_zero),
            'style': 'color: red;' if value < 0 else '',
        }
    




              