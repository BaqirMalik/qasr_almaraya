from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools import get_lang
from odoo.exceptions import UserError
import json
from datetime import timedelta
from collections import defaultdict
from datetime import datetime

class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'



    def create_column(self, name, expression_label, currency_id, figure_type, report_id, blank_if_zero, temp, temp_type, sequence):
        report_columns = self.env['account.report.column']
        if report_columns.search([('expression_label', '=', expression_label)]):
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



    def _get_aml_values(self, report, options, expanded_account_ids, offset=0, limit=None):
        limit = 800000000
        company_currency_id = self.env.user.company_id.currency_id
        non_company_currency_ids = self.env['res.currency'].search([('id', '!=', company_currency_id.id)])
        general_ledger_report_id = self.env.ref('account_reports.general_ledger_report')
        
        result = super()._get_aml_values(report, options, expanded_account_ids, offset, limit)
        
        for account_id_key in result:
            initial_balance_values = self._get_initial_balance_values(report, [account_id_key], options)
            initial_balance_dict = initial_balance_values[account_id_key][1][list(initial_balance_values[account_id_key][1].keys())[0]]
            initial_balance = initial_balance_dict.get('balance')
            all_balances = {account_id_key: {required_currency_id.id: 0 for required_currency_id in non_company_currency_ids}}
            
            original_date_from = datetime.strptime(options['date']['date_from'], "%Y-%m-%d")
            if initial_balance:
                old_records_result = self.env['account.move.line'].search([
                    ('account_id', '=', account_id_key),
                    ('date', '<', original_date_from),
                    ('parent_state', '=', 'posted'),
                ])
                all_balances = {
                    move_line.account_id.id: {non_company_currency_id.id: 0 for non_company_currency_id in non_company_currency_ids}
                    for move_line in old_records_result
                }
                for move_id in old_records_result:
                    for required_currency_id in non_company_currency_ids:
                        line_debit = move_id.debit
                        line_credit = move_id.credit
                        line_date = move_id.date
                        if required_currency_id.id == move_id.currency_id.id:
                            all_balances[move_id.account_id.id][required_currency_id.id] = all_balances[move_id.account_id.id][required_currency_id.id] + move_id.amount_currency
                        else:
                            required_currency_debit = company_currency_id.with_context(date = line_date).compute(line_debit, required_currency_id)
                            required_currency_credit = company_currency_id.with_context(date = line_date).compute(line_credit, required_currency_id)
                            all_balances[move_id.account_id.id][required_currency_id.id] = all_balances[move_id.account_id.id][required_currency_id.id] + required_currency_debit - required_currency_credit


            for date_key in result[account_id_key]:
                for forced_options_key in result[account_id_key][date_key]:
                    for required_currency_id in non_company_currency_ids:
                        all_balances
                        balance_column_name = f'custom_currency_general_ledger_balance_{required_currency_id.id}'
                        self.create_column(
                            f'Balance {required_currency_id.name}',
                            balance_column_name,
                            required_currency_id.id,
                            'monetary',
                            general_ledger_report_id.id,
                            False,
                            True,
                            'balance',
                            80,
                        )
                        line_currency = result[account_id_key][date_key][forced_options_key].get('currency_id')
                        if line_currency == required_currency_id.id:
                            amount_currency = result[account_id_key][date_key][forced_options_key].get('amount_currency')
                            all_balances[account_id_key][required_currency_id.id] = all_balances[account_id_key][required_currency_id.id] + amount_currency
                            result[account_id_key][date_key][forced_options_key][balance_column_name] = all_balances[account_id_key][required_currency_id.id]
                            # result[account_id_key][date_key][forced_options_key]['balance'] = 0
                        else:
                            line_debit = result[account_id_key][date_key][forced_options_key].get('debit', 0)
                            line_credit = result[account_id_key][date_key][forced_options_key].get('credit', 0)
                            line_date = result[account_id_key][date_key][forced_options_key].get('date', fields.Date.today())
                            required_currency_debit = company_currency_id.with_context(date = line_date).compute(line_debit, required_currency_id)
                            required_currency_credit = company_currency_id.with_context(date = line_date).compute(line_credit, required_currency_id)
                            all_balances[account_id_key][required_currency_id.id] = all_balances[account_id_key][required_currency_id.id] + required_currency_debit - required_currency_credit
                            result[account_id_key][date_key][forced_options_key][balance_column_name] = all_balances[account_id_key][required_currency_id.id]
        return result       
    

    def _get_aml_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
        line_columns = []
        for column in options['columns']:
            col_expr_label = column['expression_label']
            col_id = self.env['account.report.column'].search([('expression_label', '=', col_expr_label)])
            col_value = eval_dict[column['column_group_key']].get(col_expr_label)
            if col_id.currency_id:
                col_value = list(eval_dict.values())[0][col_id.expression_label]

            if col_value is None:
                line_columns.append({})
            else:
                col_class = 'number'

                if col_expr_label == 'amount_currency':
                    currency = self.env['res.currency'].browse(eval_dict[column['column_group_key']]['currency_id'])

                    if currency != self.env.company.currency_id:
                        formatted_value = report.format_value(col_value, currency=currency, figure_type=column['figure_type'])
                    else:
                        formatted_value = ''
                elif col_expr_label == 'date':
                    formatted_value = format_date(self.env, col_value)
                    col_class = 'date'
                elif col_expr_label == 'balance':
                    col_value += init_bal_by_col_group[column['column_group_key']]
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'], blank_if_zero=False)
                elif col_id.currency_id:
                    # col_value += init_bal_by_col_group[column['column_group_key']]
                    formatted_value = report.format_value(col_value, currency=col_id.currency_id, figure_type=column['figure_type'], blank_if_zero=False)
                elif col_expr_label == 'communication' or col_expr_label == 'partner_name':
                    col_class = 'o_account_report_line_ellipsis'
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                else:
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                    if col_expr_label not in ('debit', 'credit'):
                        col_class = ''

                line_columns.append({
                    'name': formatted_value,
                    'no_format': col_value,
                    'class': col_class,
                })

        first_column_group_key = options['columns'][0]['column_group_key']
        if eval_dict[first_column_group_key]['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move.line'

        return {
            'id': report._get_generic_line_id('account.move.line', eval_dict[first_column_group_key]['id'], parent_line_id=parent_line_id),
            'caret_options': caret_type,
            'parent_id': parent_line_id,
            'name': eval_dict[first_column_group_key]['move_name'],
            'columns': line_columns,
            'level': 2,
        }
    
    def open_journal_items(self, options, params):
        params['view_ref'] = 'airline_sc_automation.view_move_line_tree_grouped_general_general'
        action = self.env['account.report'].open_journal_items(options=options, params=params)
        action.get('context', {}).update({'search_default_group_by_account': 1})
        return action
