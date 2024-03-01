# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    use_user_restriction = fields.Boolean()
    user_ids = fields.Many2many('res.users')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        result = super().name_search(name=name, args=args, operator=operator, limit=limit)
        if self.env.user.has_group('user_journal_restriction.group_manager'):
            return result
        journal_ids = self.browse(list(map(lambda item: item[0], result))).filtered(lambda item: not item.use_user_restriction or self.env.user.id in item.user_ids.ids)
        return journal_ids.mapped(lambda journal_id: (journal_id.id, journal_id.name))


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        result = super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)
        if self.env.user.has_group('user_journal_restriction.group_manager'):
            return result
        journal_ids = self.browse(list(map(lambda item: item['id'], result))).filtered(lambda item: not item.use_user_restriction or self.env.user.id in item.user_ids.ids)
        journal_ids_by_id = {journal_id.id: journal_id for journal_id in journal_ids}
        result = list(filter(lambda item: journal_ids_by_id.get(item['id']), result))
        return result
    

    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        # res = self._search(domain, offset=offset, limit=limit, order=order, count=count)
        res = self._search(domain, offset=offset, limit=limit, order=order)
        if self.env.user.has_group('user_journal_restriction.group_manager'):
            return res if count else self.browse(res)
        return res if count else self.browse(res).filtered(lambda journal_id: not journal_id.use_user_restriction or self.env.user.id in journal_id.user_ids.ids)


    def read(self, fields=None, load='_classic_read'):
        result = super(AccountJournal, self).read(fields=fields, load=load)
        if self.env.user.has_group('user_journal_restriction.group_manager'):
            return result
        journal_int_ids = list(map(lambda item: item.get('id'), result))
        journal_ids = self.browse(journal_int_ids)
        journal_ids = journal_ids.filtered(lambda item: not item.use_user_restriction or self.env.user.id in item.user_ids.ids)
        journal_filtered_int_ids = journal_ids.ids
        return list(filter(lambda item: item.get('id') in journal_filtered_int_ids, result))
