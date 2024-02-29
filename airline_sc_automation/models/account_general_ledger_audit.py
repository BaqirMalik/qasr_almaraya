# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountGeneralLedgerReportAudit(models.Model):
    _name = "account.general.ledger.report.audit"
    _description = "Account General Ledger Report Audit"
    _rec_name = 'date'

    date = fields.Date(string="Date", default=fields.Date.today())
    search_general_name = fields.Char(string="Search")
    account_balance_ids = fields.One2many('general.balance.line', 'general_ledger_audit_id', string="General Ledger lines")

    def search_general_action(self):
        for rec in self:
            if self.search_general_name:
                query = """
                        UPDATE general_balance_line
                        SET active = (account_id IN (
                            SELECT id FROM account_account WHERE name ILIKE %s OR code ILIKE %s
                        ))
                        WHERE general_ledger_audit_id = %s
                        """
                rec.env.cr.execute(query, ('%' + rec.search_general_name + '%','%' + rec.search_general_name + '%', rec.id))
            else:
                query = """UPDATE general_balance_line
                        SET active = true WHERE
                        general_ledger_audit_id=%s"""
                rec.env.cr.execute(query, (rec.id, ))

    def update_account_balance_ids_action(self):
        for rec in self:
            for account_id in rec.account_balance_ids:
                account_id.unlink()
        account_ids_query = """SELECT DISTINCT account_id FROM account_move_line;"""
        self.env.cr.execute(account_ids_query, ())
        account_ids = rec.env.cr.dictfetchall()
        for rec in self:
            for account_id in account_ids:
                usd_currency = self.env.ref('base.USD')
                iqd_currency = self.env.ref('base.IQD')

                move_lines_query = """SELECT aml.date, aml.balance, aml.currency_id, aml.gl_audit_line_id, aml.id, aml.amount_currency
                                FROM account_move_line aml
                                JOIN account_move am ON aml.move_id = am.id
                                WHERE aml.account_id = %s
                                    AND am.state = 'posted'
                                    AND aml.date <= %s;
                                """
                self.env.cr.execute(move_lines_query, (account_id["account_id"], rec.date))
                move_lines = rec.env.cr.dictfetchall()

                balance_usd = 0
                balance_iqd = 0
                for move in move_lines:
                    if move['currency_id'] == usd_currency.id:
                        balance_usd += move['balance']
                        balance_iqd += self.env['res.currency']._get_conversion_rate(usd_currency, iqd_currency, self.env.company, move['date']) * move['balance']
                    else:
                        balance_iqd += move['amount_currency']
                        balance_usd += move['balance']

                audit_line_id = rec.account_balance_ids.create({
                    'general_ledger_audit_id': rec.id,
                    'account_id': account_id["account_id"],
                    'balance_usd': balance_usd,
                    'balance_iqd': balance_iqd,
                })
                for line in move_lines:
                    query = """UPDATE account_move_line
                            SET gl_audit_line_id = %s
                            WHERE id = %s AND gl_audit_line_id IS NULL;"""
                    self.env.cr.execute(query, (audit_line_id.id, line['id']))

    def _update_general_ids_balance(self):
        for rec in self:
            for account_balance_id in rec.account_balance_ids:
                usd_currency = self.env.ref('base.USD')
                iqd_currency = self.env.ref('base.IQD')

                move_lines_query = """SELECT aml.date, aml.balance, aml.currency_id, aml.gl_audit_line_id, aml.id, aml.amount_currency
                                FROM account_move_line aml
                                JOIN account_move am ON aml.move_id = am.id
                                WHERE aml.account_id = %s
                                    AND am.state = 'posted'
                                    AND aml.date <= %s;
                                """
                self.env.cr.execute(move_lines_query, (account_balance_id.account_id.id, rec.date))
                move_lines = rec.env.cr.dictfetchall()

                balance_usd = 0
                balance_iqd = 0
                for move in move_lines:
                    if move['currency_id'] == usd_currency.id:
                        balance_usd += move['balance']
                        balance_iqd += self.env['res.currency']._get_conversion_rate(usd_currency, iqd_currency, self.env.company, move['date']) * move['balance']
                    else:
                        balance_iqd += move['amount_currency']
                        balance_usd += move['balance']

                account_balance_id.write({
                    'balance_usd': balance_usd,
                    'balance_iqd': balance_iqd,
                })

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountGeneralLedgerReportAudit, self).create(vals_list)
        res.update_account_balance_ids_action()
        return res

    def unlink(self):
        for rec in self:
            rec.account_balance_ids.unlink()
        return super(AccountGeneralLedgerReportAudit, self).unlink()

class GeneralBalanceLine(models.Model):
    _name = "general.balance.line"
    
    general_ledger_audit_id = fields.Many2one('account.general.ledger.report.audit')
    account_id = fields.Many2one('account.account')
    balance_date = fields.Date(related='general_ledger_audit_id.date', store=True)
    balance_iqd = fields.Float()
    balance_usd = fields.Float()
    note = fields.Char()
    is_matched = fields.Boolean()
    active = fields.Boolean(default=True)
    move_line_ids = fields.One2many('account.move.line', 'gl_audit_line_id')
