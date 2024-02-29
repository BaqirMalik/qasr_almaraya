from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import datetime
from markupsafe import Markup


class ExternalPartnerLedger(models.TransientModel):
    _name = "external.partner.ledger"
    _description = "External Partner Ledger"

    date_from = fields.Date('Date From', required=True, default=datetime(datetime.now().year, 1, 1))
    date_to = fields.Date('Date To', required=True, default=fields.Date.today())
    partner_ids = fields.Many2many('res.partner', string='Partners', required=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError(_('Date From must be before Date To'))


    def print_report_action(self):
        currency_ids = self.env['res.currency'].search([('active', '=', True)])
        currency_map = {}
        partners_data = []

        for currency_id in currency_ids:
            for partner_id in self.partner_ids:
                currency_map[f"{partner_id.id}-{currency_id.id}"] = {
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
                        aml.partner_id = %s 
                        AND aml.currency_id = %s
                        AND aml.date < %s 
                        AND am.state = 'posted' 
                        AND aml.account_id IN (
                            SELECT id
                            FROM account_account
                            WHERE account_type IN ('liability_payable', 'asset_receivable') 
                            AND non_trade = False
                        )
                """
                params = (partner_id.id, currency_id.id, self.date_from)
                self.env.cr.execute(query, params)
                result = self.env.cr.fetchone()
                init_balance = result[0] if result and result[0] else 0
                currency_map[f"{partner_id.id}-{currency_id.id}"]['current_balance'] = init_balance
                currency_map[f"{partner_id.id}-{currency_id.id}"]['init_balance'] = self.format_value(init_balance, currency_id)


        for partner_id in self.partner_ids:
            partner_data = {
                'id': str(partner_id.id),
                'name': partner_id.name,
                'moves': [],
            }
            move_lines = self.env['account.move.line'].search([
                ('partner_id', '=', partner_id.id), 
                ('date', '>=', self.date_from), 
                ('date', '<=', self.date_to), 
                ('move_id.state', '=', 'posted'), 
                ('account_id.account_type', 'in', ['liability_payable', 'asset_receivable']), 
                ('account_id.non_trade', '=', False),
            ], order="date,id")
            for move_line in move_lines:
                currency_map[f"{partner_id.id}-{move_line.currency_id.id}"]['current_balance'] += move_line.amount_currency
                invoice_id = move_line.move_id
                airline_info = self.get_airline_info(invoice_id)
                memo = ""
                if move_line.payment_id:
                    memo = move_line.payment_id.ref
                else:
                    memo = move_line.name
                move_data = {
                    'date': move_line.date,
                    'debit': move_line.debit,
                    'credit': move_line.credit,
                    'order_info': airline_info['order_info'],
                    'ticket_info': airline_info['ticket_info'],
                    'memo': memo,
                    'amount_currency': self.format_value(move_line.amount_currency, move_line.currency_id)
                }
                for currency_id in currency_ids:
                    move_data[currency_map[f"{partner_id.id}-{currency_id.id}"]['key']] = self.format_value(currency_map[f"{partner_id.id}-{currency_id.id}"]["current_balance"], currency_id)
                partner_data['moves'].append(move_data)
            partners_data.append(partner_data)

        totals_data = {}
        company_currency_id = self.env.company.currency_id
        for partner_id in self.partner_ids:
            partner_total_balance = 0
            for currency_id in currency_ids:
                current_currency_balance = currency_map[f"{partner_id.id}-{currency_id.id}"]['current_balance']
                partner_total_balance += currency_id.with_context(date = self.date_to).compute(current_currency_balance, company_currency_id)
            totals_data[partner_id.id] = self.format_value(partner_total_balance, company_currency_id)

        report_data = {
            'date_to': self.date_to,
            'date_from': self.date_from,
            'currency_map': currency_map,
            'active_currency_ids': currency_ids.mapped(lambda currency_id: {'name': currency_id.name, 'key': f"balance-{currency_id.id}", 'id': str(currency_id.id), 'symbol': currency_id.symbol}),
            'data': partners_data,
            'totals_data': totals_data,
        }
        return self.env.ref('airline_sc_automation.external_partner_ledger_report_action').report_action(self, data=report_data) 



    def get_airline_info(self, invoice_id):
        line = {'order_info': '', 'ticket_info': ''}
        ticket_type = {
            'one_way': "One Way",
            'two_way': "Two Way",
            'open': "Open",
        }
        def empty_if_false(str):
            return '' if not str else str
        source_orders = False
        if invoice_id.move_type in ['out_invoice', 'out_refund']:
            source_orders = invoice_id.line_ids.sale_line_ids.order_id
        elif invoice_id.move_type in ['in_invoice', 'in_refund']:
            source_orders = invoice_id.line_ids.purchase_line_id.order_id
        source_order_id = source_orders[0] if source_orders else False
        if source_order_id:
            order_lines_description = invoice_id.invoice_line_ids.mapped(lambda line_id: empty_if_false(line_id.name))
            line['order_info'] = order_lines_description
            ticket_id = self.env['airline.ticket'].search([('sale_order_id', '=', source_order_id.id)])
            visa_id = self.env['airline.visa'].search([('sale_order_id', '=', source_order_id.id)])
            tour_id = self.env['airline.tour'].search([('sale_order_id', '=', source_order_id.id)])
            if ticket_id:
                line['order_info'] = ticket_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} \n {passenger_line.passenger_type.code} \n {empty_if_false(passenger_line.ticket_number)} \n (P: {passenger_line.price}{passenger_line.currency_id.symbol})")
                line['ticket_info'] = [
                    f"PNR: {ticket_id.pnr}", 
                    f"Route: {ticket_id.source_id.code} → {ticket_id.destination_id.code}",
                    f"Type: {ticket_type.get(ticket_id.ticket_type)}",
                    f"Date: {ticket_id.first_flight_date.strftime('%Y/%m/%d')} → {ticket_id.second_flight_date.strftime('%Y/%m/%d')}" if ticket_id.second_flight_date else f"Date: {ticket_id.first_flight_date.strftime('%Y/%m/%d')}",
                ]
            elif visa_id:
                line['ticket_info'] = [
                    f"Route: {visa_id.country_id.name}",
                    f"Type: {visa_id.residence_duration_id.name}",
                    f"Date: {visa_id.issue_date_from.strftime('%Y/%m/%d')} → {visa_id.issue_date_to.strftime('%Y/%m/%d')}",
                ]
                line['order_info'] = visa_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} - {passenger_line.passenger_type.code} - (P: {passenger_line.price}{passenger_line.currency_id.symbol})")
            elif tour_id:
                line['order_info'] = tour_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} - {passenger_line.passenger_type.code} - (P: {passenger_line.price}{passenger_line.currency_id.symbol})")
                line['ticket_info'] = [
                    f"Route: {tour_id.destination_id.name}",
                    f"Type: {tour_id.duration_id.name}",
                    f"Date: {tour_id.tour_departure_date.strftime('%Y/%m/%d')} → {tour_id.tour_return_date.strftime('%Y/%m/%d')}",
                ]
        return line


    def format_value(self, value, currency_id, figure_type='monetary', blank_if_zero=False):
        report = self.env['account.report']
        return {
            'value': report.format_value(value, currency_id, figure_type=figure_type, blank_if_zero=blank_if_zero),
            'style': 'color: red;' if value < 0 else '',
        }
    




              