# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountAccount(models.Model):
    _inherit = "account.account"

    is_used_for_purchase = fields.Boolean(string="Use For Purchase")
    is_expense_account = fields.Boolean(string="Is Expense Account")

    @api.constrains('is_used_for_purchase')
    def _check_is_used_for_purchase(self):
        if self.is_used_for_purchase == True:
            accounts = self.env['account.account'].search([('id', '!=', self.id), ('is_used_for_purchase', '=', True)])
            for account in accounts:
                account.is_used_for_purchase = False
