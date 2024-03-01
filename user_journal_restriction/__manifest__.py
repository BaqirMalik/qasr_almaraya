# -*- coding: utf-8 -*-
{
    'name': "User Journal Restriction",
    'summary': """ Helps to put access restrictions for journals. """,
    'description': """ Helps to put access restrictions for journals. """,
    'author': "AliFaleh@BasicPowered",
    'website': "https://site.basic-powered.com",
    'category': 'Accounting',
    'version': '16.0',
    'depends': ['base', 'account', 'account_accountant'],
    'data': [
        'security/res_groups.xml',
        'views/account_journal.xml',
    ],
    'license': 'Other proprietary',
}