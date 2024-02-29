# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError




class AccountPartnerLedgerReportAudit(models.Model):
    _name = "account.partner.ledger.report.audit"
    _description = "Account Partner Ledger Report Audit"
    _rec_name = 'date'

    date = fields.Date(string="Date", default=fields.Date.today())
    search_partner_name = fields.Char(string="Search")
    partner_balance_ids = fields.One2many('partner.balance.line', 'partner_ledger_audit_id', string="Partners")

    def search_partner_action(self):
        for rec in self:
            if self.search_partner_name:
                query = """
                        UPDATE partner_balance_line
                        SET active = (partner_id IN (
                            SELECT id FROM res_partner WHERE display_name ILIKE %s
                        ))
                        WHERE partner_ledger_audit_id = %s
                        """
                res = rec.env.cr.execute(query, ('%' +rec.search_partner_name + '%', rec.id))
            else:
                query = """UPDATE partner_balance_line
                        SET active = true WHERE
                        partner_ledger_audit_id=%s"""
                rec.env.cr.execute(query, (rec.id, ))

    def update_partner_balance_ids_action(self):
        for rec in self:
            for partner_id in rec.partner_balance_ids:
                partner_id.unlink()
        partner_ids = self.env['res.partner'].search([])
        for rec in self:
            usd_currency = self.env.ref('base.USD')
            iqd_currency = self.env.ref('base.IQD')
            for partner_id in partner_ids:
                usd_move_lines = self.env['account.move.line'].search([('partner_id', '=', partner_id.id), ('currency_id', '=', usd_currency.id), ('date', '<=', rec.date), ('move_id.state', '=', 'posted'), ('account_id.account_type', 'in', ['liability_payable', 'asset_receivable']), ('account_id.non_trade', '=', False)])
                iqd_move_lines = self.env['account.move.line'].search([('partner_id', '=', partner_id.id), ('currency_id', '=', iqd_currency.id), ('date', '<=', rec.date), ('move_id.state', '=', 'posted'), ('account_id.account_type', 'in', ['liability_payable', 'asset_receivable']), ('account_id.non_trade', '=', False)])
                balance_usd = sum(usd_move_lines.mapped(lambda line: line.amount_currency))
                balance_iqd = sum(iqd_move_lines.mapped(lambda line: line.amount_currency))
                audit_line_id = rec.partner_balance_ids.create({
                    'partner_ledger_audit_id': rec.id,
                    'partner_id': partner_id.id,
                    'balance_usd': balance_usd,
                    'balance_iqd': balance_iqd,
                })
                for line in usd_move_lines:
                    if not line.pl_audit_line_id:
                        line.pl_audit_line_id = audit_line_id.id
                for line in iqd_move_lines:
                    if not line.pl_audit_line_id:
                        line.pl_audit_line_id = audit_line_id.id

    def _update_partner_ids_balance(self):
        for rec in self:
            usd_currency = self.env.ref('base.USD')
            iqd_currency = self.env.ref('base.IQD')
            for partner_balance_id in rec.partner_balance_ids:
                usd_move_lines = self.env['account.move.line'].search([('partner_id', '=', partner_balance_id.partner_id.id), ('currency_id', '=', usd_currency.id), ('date', '<=', rec.date), ('move_id.state', '=', 'posted'), ('account_id.account_type', 'in', ['liability_payable', 'asset_receivable']), ('account_id.non_trade', '=', False)])
                iqd_move_lines = self.env['account.move.line'].search([('partner_id', '=', partner_balance_id.partner_id.id), ('currency_id', '=', iqd_currency.id), ('date', '<=', rec.date), ('move_id.state', '=', 'posted'), ('account_id.account_type', 'in', ['liability_payable', 'asset_receivable']), ('account_id.non_trade', '=', False)])
                balance_usd = sum(usd_move_lines.mapped(lambda line: line.amount_currency))
                balance_iqd = sum(iqd_move_lines.mapped(lambda line: line.amount_currency))
                partner_balance_id.write({
                    'balance_usd': balance_usd,
                    'balance_iqd': balance_iqd,
                })

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountPartnerLedgerReportAudit, self).create(vals_list)
        res.update_partner_balance_ids_action()
        return res

    def unlink(self):
        for rec in self:
            rec.partner_balance_ids.unlink()
        return super(AccountPartnerLedgerReportAudit, self).unlink()

class PartnerBalanceLine(models.Model):
    _name = "partner.balance.line"
    _rec_name = 'partner_id'
    partner_ledger_audit_id = fields.Many2one('account.partner.ledger.report.audit')
    partner_id = fields.Many2one('res.partner')
    balance_date = fields.Date(related='partner_ledger_audit_id.date', store=True)
    balance_iqd = fields.Float()
    balance_usd = fields.Float()
    note = fields.Char()
    is_matched = fields.Boolean()
    active = fields.Boolean(default=True)
    move_line_ids = fields.One2many('account.move.line', 'pl_audit_line_id')
