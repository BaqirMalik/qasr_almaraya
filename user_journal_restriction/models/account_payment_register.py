# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields):
        res = super(AccountPaymentRegister, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if len(active_ids) == 1 and not self.env.user.has_group('user_journal_restriction.group_manager'):
            active_id = active_ids[0]
            move_id = self.env['account.move'].browse(active_id)
            res['journal_id'] = self.env['account.journal'].search([
                ('user_ids', 'in', self.env.user.id),
                ('currency_id', '=', move_id.currency_id.id),
            ])
        return res