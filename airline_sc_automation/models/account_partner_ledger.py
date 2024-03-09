from odoo import models, _, fields
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, get_lang

from datetime import timedelta
from collections import defaultdict
from markupsafe import Markup
import os
from odoo.modules import get_module_resource
import base64


import logging
_logger = logging.getLogger(__name__)



class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    original_store_fname = fields.Char()


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'
    _description = 'Partner Ledger Custom Handler'


    def get_custom_css(self):
        debit_index = 0
        report_id = self.env.ref('account_reports.partner_ledger_report')
        active_columns = self.env['account.report.column'].search([('report_id', '=', report_id.id)])
        for index, column in enumerate(active_columns):
            if column.temp_type == 'debit' and not column.temp:
                debit_index = index
        custom_css = """
            body > div.o_action_manager > div > div.o_content > div > div.o_account_reports_page.o_account_reports_no_print > div.table-responsive > table > thead > tr:nth-child(2) > th:nth-child(%d){
                display: none !important;
            }
            body > div.o_action_manager > div > div.o_content > div > div.o_account_reports_page.o_account_reports_no_print > div.table-responsive > table > tbody > tr:nth-child(4) > td:nth-child(%d){
                display: none !important;
            }
        """%(debit_index + 2, debit_index + 2)        
        return custom_css.replace(' ', '').replace('\t', '').replace('\n', '').encode('utf-8')

    def update_styles(self):
        attachment_model = self.env['ir.attachment']
        assets_backend_record_id = attachment_model.search([('name', '=', 'web.assets_backend.min.css')])
        if not assets_backend_record_id.original_store_fname:
            assets_backend_record_id.original_store_fname = assets_backend_record_id.store_fname
        file_store_path = attachment_model._filestore()
        assets_backend_file_path = os.path.join(file_store_path, assets_backend_record_id.original_store_fname)
        assets_backend_file = open(assets_backend_file_path, 'rb')
        assets_backend_file_content = assets_backend_file.read()
        assets_backend_file.close()
        new_assets_backend_file_content = assets_backend_file_content + self.get_custom_css()
        assets_backend_record_id.write({
            'datas': base64.b64encode(new_assets_backend_file_content),
            'mimetype': 'text/css',
        })



    def update_totals(self, totals, index, currency_id, value):
        if not totals.get(index):
            totals[index] = {
                'currency_id': currency_id,
                'value': 0,
            }
        totals[index]['value'] += value

    # def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
    #     lines = super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings='warnings')
    #     report_id = self.env.ref('account_reports.partner_ledger_report')
    #     partner_ledger_column_ids = self.env['account.report.column'].search([('report_id', '=', report_id.id)])
    #     original_column_ids = [
    #         self.env.ref('account_reports.partner_ledger_report_debit').id,
    #         self.env.ref('account_reports.partner_ledger_report_credit').id,
    #         self.env.ref('account_reports.partner_ledger_report_balance').id,
    #     ]
    #     company_currency_id = self.env.company.currency_id
    #     columns_instructions = {}
    #     report = self.env['account.report']
    #     for index, column in enumerate(partner_ledger_column_ids):
    #         if column.id in original_column_ids:
    #             columns_instructions[index] = {
    #                 'column_id': column,
    #                 'action_type': 'original',
    #                 'column_type': column.temp_type,
    #             }
    #         elif column.temp:
    #             columns_instructions[index] = {
    #                 'column_id': column,
    #                 'action_type': 'temp',
    #                 'column_type': column.temp_type,
    #             }
    #
    #     totals = {}
    #
    #     for lines_index, line in enumerate(lines[:-1]):
    #         try:
    #             partner_int_id = int(line[1]['id'].split('~')[-1].split('-')[-1])
    #         except:
    #             continue
    #         for column_index, column in enumerate(line[1]['columns']):
    #             if column_index in columns_instructions:
    #                 if columns_instructions[column_index]['action_type'] == 'original':
    #                     move_lines = self.env['account.move.line'].search([('partner_id', '=', partner_int_id), ('currency_id', '=', company_currency_id.id), ('move_id.state', '=', 'posted'), ('account_id.account_type', 'in', ['liability_payable', 'asset_receivable']), ('account_id.non_trade', '=', False)])
    #                     if columns_instructions[column_index]['column_type'] == 'debit':
    #                         value = sum([x.debit for x in move_lines])
    #                         self.update_totals(totals, column_index, company_currency_id, value)
    #                         name = report.format_value(value, company_currency_id, figure_type='monetary', blank_if_zero=False)
    #                         lines[lines_index][1]['columns'][column_index] = {
    #                             'name': name,
    #                             'no_format': value,
    #                             'class': 'number'
    #                         }
    #                     elif columns_instructions[column_index]['column_type'] == 'credit':
    #                         value = sum([x.credit for x in move_lines])
    #                         self.update_totals(totals, column_index, company_currency_id, value)
    #                         name = report.format_value(value, company_currency_id, figure_type='monetary', blank_if_zero=False)
    #                         lines[lines_index][1]['columns'][column_index] = {
    #                             'name': name,
    #                             'no_format': value,
    #                             'class': 'number'
    #                         }
    #                     elif columns_instructions[column_index]['column_type'] == 'balance':
    #                         value = sum([x.balance for x in move_lines])
    #                         self.update_totals(totals, column_index, company_currency_id, value)
    #                         name = report.format_value(value, company_currency_id, figure_type='monetary', blank_if_zero=False)
    #                         lines[lines_index][1]['columns'][column_index] = {
    #                             'name': name,
    #                             'no_format': value,
    #                             'class': 'number'
    #                         }
    #                 elif columns_instructions[column_index]['action_type'] == 'temp':
    #                     move_lines = self.env['account.move.line'].search([('partner_id', '=', partner_int_id), ('currency_id', '=', columns_instructions[column_index]['column_id'].currency_id.id), ('move_id.state', '=', 'posted'), ('account_id.account_type', 'in', ['liability_payable', 'asset_receivable']), ('account_id.non_trade', '=', False)])
    #                     column_currency_id = columns_instructions[column_index]['column_id'].currency_id
    #                     if columns_instructions[column_index]['column_type'] == 'debit':
    #                         value = sum([x.amount_currency if x.amount_currency > 0 else 0  for x in move_lines])
    #                         self.update_totals(totals, column_index, column_currency_id, value)
    #                         name = report.format_value(value, column_currency_id, figure_type='monetary', blank_if_zero=False)
    #                         lines[lines_index][1]['columns'][column_index] = {
    #                             'name': name,
    #                             'no_format': value,
    #                             'class': 'number'
    #                         }
    #                     elif columns_instructions[column_index]['column_type'] == 'credit':
    #                         value = sum([x.amount_currency if x.amount_currency < 0 else 0  for x in move_lines])
    #                         self.update_totals(totals, column_index, column_currency_id, value)
    #                         name = report.format_value(value, column_currency_id, figure_type='monetary', blank_if_zero=False)
    #                         lines[lines_index][1]['columns'][column_index] = {
    #                             'name': name,
    #                             'no_format': value,
    #                             'class': 'number'
    #                         }
    #                     elif columns_instructions[column_index]['column_type'] == 'balance':
    #                         value = sum([x.amount_currency for x in move_lines])
    #                         self.update_totals(totals, column_index, column_currency_id, value)
    #                         name = report.format_value(value, column_currency_id, figure_type='monetary', blank_if_zero=False)
    #                         lines[lines_index][1]['columns'][column_index] = {
    #                             'name': name,
    #                             'no_format': value,
    #                             'class': 'number'
    #                         }
    #     for total_index in totals:
    #         value = totals[total_index]['value']
    #         name = report.format_value(value, totals[total_index]['currency_id'], figure_type='monetary', blank_if_zero=False)
    #         lines[-1][1]['columns'][total_index] = {
    #             'name': name,
    #             'no_format': value,
    #             'class': 'number'
    #         }
    #     return lines


    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        limit = 800000000
        result = super()._get_aml_values(options, partner_ids, offset, limit)
        company_currency_id = self.env.user.company_id.currency_id
        new_columns = []
        ticket_type = {
            'one_way': "One Way",
            'two_way': "Two Way",
            'open': "Open",
        }
        for partner_id in result:
            current_partner_lines = result[partner_id]
            for line in current_partner_lines:
                currency_id = line.get('currency_id', False)
                line['balance'] = 0
                if currency_id:
                    currency_id = self.env['res.currency'].browse(currency_id)
                    if currency_id.id != company_currency_id.id:
                        partner_ledger_report_id = self.env.ref('account_reports.partner_ledger_report')
                        debit_column_name = f'custom_currency_debit_{currency_id.id}'
                        credit_column_name =  f'custom_currency_credit_{currency_id.id}'
                        balance_column_name = f'custom_currency_balance_{currency_id.id}'
                        new_columns.append(credit_column_name)
                        new_columns.append(debit_column_name)
                        new_columns.append(balance_column_name)
                        self.create_column(
                            f'Debit {currency_id.name}',
                            debit_column_name,
                            currency_id.id,
                            'monetary',
                            partner_ledger_report_id.id,
                            True,
                            True,
                            'debit',
                            11,
                        )
                        self.create_column(
                            f'Credit {currency_id.name}',
                            credit_column_name,
                            currency_id.id,
                            'monetary',
                            partner_ledger_report_id.id,
                            True,
                            True,
                            'credit',
                            13,
                        )
                        self.create_column(
                            f'Balance {currency_id.name}',
                            balance_column_name,
                            currency_id.id,
                            'monetary',
                            partner_ledger_report_id.id,
                            False,
                            True,
                            'balance',
                            16,
                        )

        temp_columns = self.env['account.report.column'].search([('temp', '=', True)])


        for partner_id in result:
            current_partner_lines = result[partner_id]
            for line in current_partner_lines:
                move_name = line.get('move_name', 'None')
                move_type = line.get('move_type', 'None')
                payment_id = line.get('payment_id', False)
                line['ticket_customer'] = ""
                line['ticket_vendor'] = ""
                line['passengers_info'] = ""
                line['ticket_info'] = ""
                line['ticket_flight_number'] = ""
                line['balance'] = 0
                line['memo'] = ""
                line['order_description'] = ""
                line['source_document'] = ""

                def empty_if_false(str):
                    return '' if not str else str
                
                for column in temp_columns:
                    line[column.expression_label] = column.get_default_value()

                if move_type in ['out_invoice', 'out_refund']:
                    invoice_name = line.get('move_name', 'No Name')
                    invoice_id = self.env['account.move'].search([('name', '=', invoice_name), ('partner_id', '=', partner_id)])
                    source_orders = invoice_id.line_ids.sale_line_ids.order_id
                    source_order_id = source_orders[0] if source_orders else False
                    if source_order_id:
                        order_lines_description = Markup('<br/>').join(invoice_id.invoice_line_ids.mapped('name'))
                        line['passengers_info'] = order_lines_description
                        ticket_id = self.env['airline.ticket'].search([('sale_order_id', '=', source_order_id.id)])
                        visa_id = self.env['airline.visa'].search([('sale_order_id', '=', source_order_id.id)])
                        tour_id = self.env['airline.tour'].search([('sale_order_id', '=', source_order_id.id)])
                        if ticket_id:
                            line['ticket_customer'] = ticket_id.customer_id.name
                            line['ticket_vendor'] = ticket_id.vendor_id.name
                            line['passengers_info'] = Markup('<br/>').join(ticket_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} - {passenger_line.passenger_type.code} - {passenger_line.ticket_number} - (P: {passenger_line.price}{passenger_line.currency_id.symbol})"))
                            line['ticket_info'] = Markup('<br/>').join([
                                f"PNR: {ticket_id.pnr}", 
                                f"Route: {ticket_id.source_id.code} → {ticket_id.destination_id.code}",
                                f"Type: {ticket_type.get(ticket_id.ticket_type)}",
                                f"Date: {ticket_id.first_flight_date.strftime('%Y/%m/%d')} → {ticket_id.second_flight_date.strftime('%Y/%m/%d')}" if ticket_id.second_flight_date else f"{ticket_id.first_flight_date.strftime('%Y/%m/%d')}",
                            ])
                            line['ticket_flight_number'] = ticket_id.flight_number
                            line['source_document'] = ticket_id.name
                        elif visa_id:
                            line['ticket_customer'] = visa_id.customer_id.name
                            line['ticket_vendor'] = visa_id.vendor_id.name
                            line['ticket_info'] = Markup('<br/>').join([
                                f"Route: {visa_id.country_id.name}",
                                f"Type: {visa_id.residence_duration_id.name}",
                                f"Date: {visa_id.issue_date_from.strftime('%Y/%m/%d')} → {visa_id.issue_date_to.strftime('%Y/%m/%d')}",
                            ])
                            line['passengers_info'] = Markup('<br/>').join(visa_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} - {passenger_line.passenger_type.code} - (P: {passenger_line.price}{passenger_line.currency_id.symbol})"))
                            line['source_document'] = visa_id.name
                        elif tour_id:
                            line['ticket_customer'] = tour_id.customer_id.name
                            line['ticket_vendor'] = tour_id.vendor_id.name
                            line['passengers_info'] = Markup('<br/>').join(tour_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} - {passenger_line.passenger_type.code} - (P: {passenger_line.price}{passenger_line.currency_id.symbol})"))
                            line['ticket_info'] = Markup('<br/>').join([
                                f"Route: {tour_id.destination_id.name}",
                                f"Type: {tour_id.duration_id.name}",
                                f"Date: {tour_id.tour_departure_date.strftime('%Y/%m/%d')} → {tour_id.tour_return_date.strftime('%Y/%m/%d')}",
                            ])
                            line['source_document'] = tour_id.name
                elif move_type in ['in_invoice', 'in_refund']:
                    invoice_name = line.get('move_name', 'No Name')
                    invoice_id = self.env['account.move'].search([('name', '=', invoice_name), ('partner_id', '=', partner_id)])
                    source_orders = invoice_id.line_ids.purchase_line_id.order_id
                    source_order_id = source_orders[0] if source_orders else False
                    if source_order_id:
                        ticket_id = self.env['airline.ticket'].search([('purchase_order_id', '=', source_order_id.id)])
                        visa_id = self.env['airline.visa'].search([('purchase_order_id', '=', source_order_id.id)])
                        tour_id = self.env['airline.tour'].search([('purchase_order_id', '=', source_order_id.id)])
                        if ticket_id:
                            line['ticket_customer'] = ticket_id.customer_id.name
                            line['ticket_vendor'] = ticket_id.vendor_id.name
                            line['passengers_info'] = Markup('<br/>').join(ticket_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} - {passenger_line.passenger_type.code} - {passenger_line.ticket_number} - (C: {passenger_line.cost}{passenger_line.vendor_currency_id.symbol})"))
                            line['ticket_flight_number'] = ticket_id.flight_number
                            line['ticket_info'] = Markup('<br/>').join([
                                f"PNR: {ticket_id.pnr}", 
                                f"Route: {ticket_id.source_id.code} → {ticket_id.destination_id.code}",
                                f"Type: {ticket_type.get(ticket_id.ticket_type)}",
                                f"Date: {ticket_id.first_flight_date.strftime('%Y/%m/%d')} → {ticket_id.second_flight_date.strftime('%Y/%m/%d')}" if ticket_id.second_flight_date else f"{ticket_id.first_flight_date.strftime('%Y/%m/%d')}",
                            ])
                            line['source_document'] = ticket_id.name
                        elif visa_id:
                            line['ticket_customer'] = visa_id.customer_id.name
                            line['ticket_vendor'] = visa_id.vendor_id.name
                            line['passengers_info'] = Markup('<br/>').join(visa_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} - {passenger_line.passenger_type.code} - (C: {passenger_line.cost}{passenger_line.vendor_currency_id.symbol})"))
                            line['ticket_info'] = Markup('<br/>').join([
                                f"Route: {visa_id.country_id.name}",
                                f"Type: {visa_id.residence_duration_id.name}",
                                f"Date: {visa_id.issue_date_from.strftime('%Y/%m/%d')} → {visa_id.issue_date_to.strftime('%Y/%m/%d')}",
                            ])
                            line['source_document'] = visa_id.name
                        elif tour_id:
                            line['ticket_customer'] = tour_id.customer_id.name
                            line['ticket_vendor'] = tour_id.vendor_id.name
                            line['passengers_info'] = Markup('<br/>').join(tour_id.passenger_ids.mapped(lambda passenger_line: f"{empty_if_false(passenger_line.passenger_id.name)} - {passenger_line.passenger_type.code} - (C: {passenger_line.cost}{passenger_line.vendor_currency_id.symbol})"))
                            line['ticket_info'] = Markup('<br/>').join([
                                f"Route: {tour_id.destination_id.name}",
                                f"Type: {tour_id.duration_id.name}",
                                f"Date: {tour_id.tour_departure_date.strftime('%Y/%m/%d')} → {tour_id.tour_return_date.strftime('%Y/%m/%d')}",
                            ])
                            line['source_document'] = tour_id.name
                if payment_id:
                    line['memo'] = self.env['account.payment'].browse(payment_id).ref
                else:
                    line['memo'] = self.env['account.move.line'].browse(line.get('id')).name

                currency_id = line.get('currency_id', False)
                if currency_id:
                    currency_id = self.env['res.currency'].browse(currency_id)
                    if currency_id.id != company_currency_id.id:
                        debit_column_name = f'custom_currency_debit_{currency_id.id}'
                        credit_column_name =  f'custom_currency_credit_{currency_id.id}'
                        balance_column_name = f'custom_currency_balance_{currency_id.id}' 
                        original_amount_currency = line.get('amount_currency')
                        line['debit'] = 0
                        line['credit'] = 0
                        line['balance'] = 0
                        line[debit_column_name] = original_amount_currency if original_amount_currency > 0 else 0
                        line[credit_column_name] = original_amount_currency * -1 if original_amount_currency < 0 else 0
                        line[balance_column_name] = 0



        initial_balance_values = self._get_initial_balance_values(list(result.keys()), options)


        for partner_id in result:
            partner_initial_balance_values = list(initial_balance_values[partner_id].values())[0]
            initial_balance = partner_initial_balance_values.get('balance', 0)
            cumulative_balance = initial_balance
            if not cumulative_balance:
                    cumulative_balance = 0
            current_partner_lines = result[partner_id]
            for line in current_partner_lines:
                amount_to_add = (line['amount_currency'] if line['currency_id'] == company_currency_id.id else 0)
                if not amount_to_add:
                    amount_to_add = 0
                cumulative_balance = cumulative_balance + amount_to_add
                line['balance'] = cumulative_balance

        
        temp_currencies = [col.currency_id for col in temp_columns]

        for partner_id in result:
            current_partner_lines = result[partner_id]
            partner_initial_balance_values = list(initial_balance_values[partner_id].values())[0]
            for currency_id in temp_currencies:
                balance_column_name = f'custom_currency_balance_{currency_id.id}'
                initial_balance = partner_initial_balance_values.get(balance_column_name, False)
                cumulative_balance = initial_balance
                for line in current_partner_lines:
                    if line['currency_id'] == currency_id.id:
                        cumulative_balance = cumulative_balance + line['amount_currency']
                    line[balance_column_name] = cumulative_balance

        for partner_id in result:
            current_partner_lines = result[partner_id]
            if current_partner_lines:
                last_partner_line = current_partner_lines[-1]
                total_line = {'id': None, 'date': 'Total', 'date_maturity': 'Total', 'name': 'Total', 'ref': '', 'company_id': 1, 'account_id': 1706, 'payment_id': 776, 'partner_id': None, 'currency_id': company_currency_id.id, 'amount_currency': None, 'matching_number': None, 'debit': None, 'credit': None, 'balance': 0.0, 'move_name': 'Total', 'move_type': None, 'account_code': '', 'account_name': '', 'journal_code': '', 'journal_name': '', 'column_group_key': last_partner_line['column_group_key'], 'key': 'directly_linked_aml', 'ticket_customer': '', 'ticket_vendor': '', 'passengers_info': '', 'ticket_info': '', 'ticket_flight_number': '', 'memo': "Total All Currencies", 'order_description': '', 'source_document': ''}
                for temp_column in temp_columns:
                    total_line[temp_column.expression_label] = 0
                temp_balance_columns = self.env['account.report.column'].search([('temp', '=', True), ('temp_type', '=', 'balance')])
                total_line['balance'] = last_partner_line['balance']
                for temp_column in temp_balance_columns:
                    column_in_company_currency = temp_column.currency_id.with_context(date = last_partner_line.get('date')).compute(last_partner_line.get(temp_column.expression_label), company_currency_id)
                    total_line['balance'] += column_in_company_currency
                    total_line[temp_column.expression_label] = None
                current_partner_lines.append(total_line)
        # raise UserError(str(result))
        # report_columns.delete_unused_columns(new_columns)
        # raise UserError(str(result))
        return result
    


    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        if aml_query_result['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move.line'

        columns = []
        report = self.env['account.report']
        temp_columns = self.env['account.report.column'].search([('temp', '=', True)])
        temp_columns_names = list(temp_columns.mapped('expression_label'))
        currency = self.env['res.currency'].browse(aml_query_result['currency_id'])
        for column in options['columns']:
            col_expr_label = column['expression_label']


            if col_expr_label == 'ref':
                col_value = report._format_aml_name(aml_query_result['name'], aml_query_result['ref'], aml_query_result['move_name'])
            else:
                col_value = aml_query_result[col_expr_label] if column['column_group_key'] == aml_query_result['column_group_key'] else None

            if col_value is None:
                columns.append({})
            else:
                col_class = 'number'

                if col_expr_label in temp_columns_names:
                    currency = self.env['account.report.column'].search([('expression_label', '=', col_expr_label)]).currency_id
                    formatted_value = report.format_value(col_value, currency=currency, figure_type=column['figure_type'], blank_if_zero=column['blank_if_zero'])
                elif col_expr_label == 'date_maturity':
                    formatted_value = format_date(self.env, fields.Date.from_string(col_value))
                    col_class = 'date'
                elif col_expr_label == 'amount_currency':
                    currency = self.env['res.currency'].browse(aml_query_result['currency_id'])
                    formatted_value = report.format_value(col_value, currency=currency, figure_type=column['figure_type'], blank_if_zero=column['blank_if_zero'])
                elif col_expr_label == 'balance':
                    # col_value += init_bal_by_col_group[column['column_group_key']]
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'],currency=currency, blank_if_zero=column['blank_if_zero'])
                else:

                    if col_expr_label == 'ref':
                        col_class = 'o_account_report_line_ellipsis'
                    elif col_expr_label not in ('debit', 'credit'):
                        col_class = ''
                    formatted_value = report.format_value(col_value, currency=currency, figure_type=column['figure_type'], blank_if_zero=column['blank_if_zero'])

                columns.append({
                    'name': formatted_value,
                    'no_format': col_value,
                    'class': col_class,
                })

        res = {
            'id': report._get_generic_line_id('account.move.line', aml_query_result['id'], parent_line_id=partner_line_id),
            'parent_id': partner_line_id,
            'name': format_date(self.env, aml_query_result['date']),
            'class': 'text-muted' if aml_query_result['key'] == 'indirectly_linked_aml' else 'text',  # do not format as date to prevent text centering
            'columns': columns,
            'caret_options': caret_type,
            'level': 2 + level_shift,
        }

        return res


    def create_column(self, name, expression_label, currency_id, figure_type, report_id, blank_if_zero, temp, temp_type, sequence):
        report_columns = self.env['account.report.column']
        if report_columns.search([('expression_label', '=', expression_label), ('active', 'in', [True, False])]):
            return
        report_columns.create({
            'name': name,
            'expression_label': expression_label,
            'currency_id': currency_id,
            'figure_type': figure_type,
            'report_id': report_id,
            'blank_if_zero': blank_if_zero,
            'temp': temp,
            'temp_type': temp_type,
            'sequence': sequence,
        })




    def _get_initial_balance_values(self, partner_ids, options):
        queries = []
        params = []
        report = self.env.ref('account_reports.partner_ledger_report')
        # ct_query = self.env['res.currency']._get_query_currency_table(options)
        ct_query = self.env['res.currency']._get_query_currency_table(self.env.companies.ids, fields.Date.today())
        _logger.warning(f"[ct_query] => {ct_query}")


        company_currency_id = self.env.user.company_id.currency_id
        temp_columns = self.env['account.report.column'].search([('temp', '=', True), ('active', 'in', [True, False])])

        temp_columns_dict = {f'{col.currency_id.id}': [] for col in temp_columns}

        for column in temp_columns:
            temp_columns_dict[str(column.currency_id.id)].append(column)

        temp_columns_query = ""

        for temp_columns_key in temp_columns_dict:
            currency_columns = temp_columns_dict[temp_columns_key]
            balance_column = list(filter(lambda item: item.temp_type == 'balance', currency_columns))[0]
            debit_column = list(filter(lambda item: item.temp_type == 'debit', currency_columns))[0]
            credit_column = list(filter(lambda item: item.temp_type == 'credit', currency_columns))[0]
            amount_currency = f"SUM(CASE WHEN account_move_line.currency_id = {balance_column.currency_id.id} THEN ROUND(account_move_line.amount_currency) END)"
            temp_columns_query += f",{amount_currency} AS {balance_column.expression_label}"
            temp_columns_query += f",CASE WHEN {amount_currency} >= 0 THEN {amount_currency} ELSE 0 END   AS {debit_column.expression_label}"
            temp_columns_query += f",CASE WHEN {amount_currency} < 0 THEN ABS({amount_currency}) ELSE 0 END   AS {credit_column.expression_label}"


        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            # Get sums for the initial balance.
            # period: [('date' <= options['date_from'] - 1)]
            new_options = self._get_options_initial_balance(column_group_options)
            tables, where_clause, where_params = report._query_get(new_options, 'normal', domain=[('partner_id', 'in', partner_ids)])
            _logger.warning(f"[table] => {tables}")
            _logger.warning(f"[where] => {where_clause} => {where_params}")
            # where_clause = f'({where_clause}) AND ("account_move_line"."currency_id" = {company_currency_id.id})'
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    account_move_line.partner_id,
                    %s                                                                                    AS column_group_key,
                    SUM(CASE WHEN account_move_line.currency_id = {company_currency_id.id} THEN ROUND(account_move_line.debit * currency_table.rate, currency_table.precision) END)   AS debit,
                    SUM(CASE WHEN account_move_line.currency_id = {company_currency_id.id} THEN ROUND(account_move_line.credit * currency_table.rate, currency_table.precision) END)  AS credit,
                    SUM(CASE WHEN account_move_line.currency_id = {company_currency_id.id} THEN ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END) AS balance
                    {temp_columns_query}
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.partner_id
            """)

            # raise UserError(queries[0])

        self._cr.execute(" UNION ALL ".join(queries), params)

        init_balance_by_col_group = {
            partner_id: {column_group_key: {} for column_group_key in options['column_groups']}
            for partner_id in partner_ids
        }
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['partner_id']][result['column_group_key']] = result

        return init_balance_by_col_group

    def open_journal_items(self, options, params):
        params['view_ref'] = 'airline_sc_automation.view_move_line_tree_grouped_general_partner'
        action = self.env['account.report'].open_journal_items(options=options, params=params)
        action.get('context', {}).update({'search_default_group_by_account': 0, 'search_default_group_by_partner': 1})
        return action

class AccountReportColumn(models.Model):
    _inherit = 'account.report.column'
    _order = "sequence,id"

    temp = fields.Boolean()
    sequence = fields.Integer()
    currency_id = fields.Many2one('res.currency')
    temp_type = fields.Char()
    active = fields.Boolean(default=True)
    can_be_deactivated = fields.Boolean(default=True)

    def delete_unused_columns(self, columns):
        self.search([('temp', '=', True), ('expression_label', 'not in', columns)]).sudo().unlink()


    def get_default_value(self):
        if self.figure_type == 'none':
            return ''
        elif self.figure_type == 'monetary':
            return 0