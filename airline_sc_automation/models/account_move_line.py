# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"


    def button_draft(self):
        has_group = self.env.user.has_group('airline_sc_automation.group_can_delete_audited_journal_item')
        for rec in self:
            for move in rec.line_ids:
                if not has_group and (move.pl_audit_line_id.is_matched or move.is_pl_audited):
                    raise UserError("You don't have access to reset it, because the Journal Items are audited in Partner Ledger Audit. Please contact your administration first.")
                elif not has_group and (move.gl_audit_line_id.is_matched or move.is_gl_audited):
                    raise UserError("You don't have access to reset it, because the Journal Items are audited in General Ledger Audit. Please contact your administration first.")
        return super(AccountMove, self).button_draft()

    def unlink(self):
        has_group = self.env.user.has_group('airline_sc_automation.group_can_delete_audited_journal_item')
        for rec in self:
            for move in rec.line_ids:
                if not has_group and (move.pl_audit_line_id.is_matched or rec.is_pl_audited):
                    raise UserError("You don't have access to delete it, because it's audited in Partner Ledger Audit. Please contact your administration first.")
                elif not has_group and (move.gl_audit_line_id.is_matched or rec.is_gl_audited):
                    raise UserError("You don't have access to delete it, because it's audited in General Ledger Audit. Please contact your administration first.")
                elif has_group:
                    old_pl_audit_id = move.pl_audit_line_id.partner_ledger_audit_id
                    old_gl_audit_id = move.gl_audit_line_id.general_ledger_audit_id
                    pl_audit_id = self.env['account.partner.ledger.report.audit'].search([('date', '>', move.pl_audit_line_id.partner_ledger_audit_id.date)], limit=1, order="date asc")
                    gl_audit_id = self.env['account.general.ledger.report.audit'].search([('date', '>', move.gl_audit_line_id.general_ledger_audit_id.date)], limit=1, order="date asc")
                    move_line_ids = self.env['account.move.line'].search([('date', '>=', move.date)])

                    for move_line in move_line_ids:
                        if pl_audit_id:
                            pl_audit_line_id = pl_audit_id.partner_balance_ids.filtered(lambda x: x.partner_id == move_line.partner_id)
                            move.pl_audit_line_id = pl_audit_line_id.id if pl_audit_line_id else False
                        if gl_audit_id:
                            gl_audit_line_id = gl_audit_id.account_balance_ids.filtered(lambda x: x.account_id == move_line.account_id)
                            move.gl_audit_line_id = gl_audit_line_id.id if gl_audit_line_id else False

                    if pl_audit_id:
                        pl_audit_id._update_partner_ids_balance()
                    if gl_audit_id:
                        gl_audit_id._update_general_ids_balance()

                    old_gl_audit_id.write({'date': move.date})
                    old_gl_audit_id._update_general_ids_balance()
                    old_pl_audit_id.write({'date': move.date})
                    old_pl_audit_id._update_partner_ids_balance()

        return super(AccountMove, self).unlink()
    
    def action_post(self):
        res = super(AccountMove, self).action_post()
        check_audited = False
        for rec in self.line_ids:
            check_audited = rec._check_audited()
        if check_audited:
            for rec in self.line_ids:
                rec._onchange_is_gl_audited({'is_gl_audited': False})
                rec._onchange_is_pl_audited({'is_pl_audited': False})

        return res

    
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _order="date,id"

    AUDIT_STATE_SELECTION = [
        ('not_audited', 'Not Audited'),
        ('matched', 'Matched'),
        ('not_matched', 'Not Matched'),
    ]

    gl_audit_line_id = fields.Many2one('general.balance.line', string="General Ledger Audit Line")
    pl_audit_line_id = fields.Many2one('partner.balance.line', string="Partner Ledger Audit Line")
    gl_audit_state = fields.Selection(AUDIT_STATE_SELECTION, compute="_compute_gl_audit_state")
    pl_audit_state = fields.Selection(AUDIT_STATE_SELECTION, compute="_compute_pl_audit_state")
    gl_audit_note = fields.Char(related='gl_audit_line_id.note')
    pl_audit_note = fields.Char(related='pl_audit_line_id.note')

    is_gl_audited = fields.Boolean(string="Is GL Audited", default=False)
    is_pl_audited = fields.Boolean(string="Is PL Audited", default=False)
    gl_note = fields.Char(string="GL Note")
    pl_note = fields.Char(string="PL Note")

    def _check_audited(self):
        for rec in self:
            gl_move_lines = self.env['account.move.line'].search([('account_id', '=', rec.account_id.id), ('date', '>=', rec.date), ('is_gl_audited','=', True)])
            pl_move_lines = self.env['account.move.line'].search([('partner_id', '=', rec.partner_id.id), ('date', '>=', rec.date), ('is_pl_audited','=', True)])
            has_group = self.env.user.has_group('airline_sc_automation.group_can_audit_journal_item')

            if not has_group and gl_move_lines:
                raise UserError("There is audited Lines in General Ledger, please contact your administration.")
            elif not has_group and pl_move_lines:
                raise UserError("There is audited Lines in Partner Ledger, please contact your administration.")
            else:
                return has_group

    def _onchange_is_gl_audited(self, vals):
        has_group = self.env.user.has_group('airline_sc_automation.group_can_audit_journal_item')
        if not has_group:
            raise UserError("You don't have access to audit it, please contact your administration.")

        for line in self:
            move_lines = self.env['account.move.line'].search([('account_id', '=', line.account_id.id), ('date', '<=', line.date), ('is_gl_audited','=', False)])
            if vals.get('is_gl_audited'):
                for move in move_lines:
                    move.write({'is_gl_audited': True})
            if vals.get('is_gl_audited') == False:
                move_lines = self.env['account.move.line'].search([('account_id', '=', line.account_id.id), ('date', '>=', line.date), ('is_gl_audited','=', True)])
                for move in move_lines:
                    move.write({'is_gl_audited': False})
                    move.write({'gl_note': ''})


    def _onchange_is_pl_audited(self, vals):
        has_group = self.env.user.has_group('airline_sc_automation.group_can_audit_journal_item')
        if not has_group:
            raise UserError("You don't have access to audit it, please contact your administration.")
        for line in self:
            move_lines = self.env['account.move.line'].search([('partner_id', '=', line.partner_id.id), ('date', '<=', line.date), ('is_pl_audited','=', False)])
            if vals.get('is_pl_audited'):
                for move in move_lines:
                    move.write({'is_pl_audited': True})
            if vals.get('is_pl_audited') == False:
                move_lines = self.env['account.move.line'].search([('partner_id', '=', line.partner_id.id), ('date', '>=', line.date), ('is_pl_audited','=', True)])
                for move in move_lines:
                    move.write({'is_pl_audited': False})
                    move.write({'pl_note': ''})
                    
    def write(self, vals):
        check_audited = False
        for rec in self:
            check_audited = rec._check_audited()
        if check_audited:
            if not self.env.context.get('skip_audit'):
                for rec in self:
                    new_context = dict(self.env.context, skip_audit=True)
                    self.env.context = new_context
                    if vals.get('is_gl_audited') == False or vals.get('is_gl_audited') == True:
                        rec._onchange_is_gl_audited(vals)
                    if vals.get('is_pl_audited') == False or vals.get('is_pl_audited') == True:
                        rec._onchange_is_pl_audited(vals)

        res = super(AccountMoveLine, self).write(vals)
        return res

    def _compute_gl_audit_state(self):
        for rec in self:
            if rec.gl_audit_line_id:
                if rec.gl_audit_line_id.is_matched:
                    rec.gl_audit_state = 'matched'
                else:
                    rec.gl_audit_state = 'not_matched'
            else:
                rec.gl_audit_state = 'not_audited'


    def _compute_pl_audit_state(self):
        for rec in self:
            if rec.pl_audit_line_id:
                if rec.pl_audit_line_id.is_matched:
                    rec.pl_audit_state = 'matched'
                else:
                    rec.pl_audit_state = 'not_matched'
            else:
                rec.pl_audit_state = 'not_audited'

    def unlink(self):
        has_group = self.env.user.has_group('airline_sc_automation.group_can_delete_audited_journal_item')
        for rec in self:
            if not has_group and (rec.pl_audit_line_id.is_matched or rec.is_pl_audited):
                raise UserError("You don't have access to delete it, because it's audited in Partner Ledger Audit. Please contact your administration first.")
            elif not has_group and (rec.gl_audit_line_id.is_matched or rec.is_gl_audited):
                raise UserError("You don't have access to delete it, because it's audited in General Ledger Audit. Please contact your administration first.")

            if rec.is_gl_audited:
                rec._onchange_is_gl_audited({'is_gl_audited': False})
            if rec.is_pl_audited:
                rec._onchange_is_pl_audited({'is_pl_audited': False})
        return super(AccountMoveLine, self).unlink()



