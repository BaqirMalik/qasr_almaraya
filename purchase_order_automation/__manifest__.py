{
    'name' : 'Purchase Order Automation',
    'version' : '1.0',
    'author':'AliFaleh@BasicPowered',
    'category': 'purchase',
    'summary': """Enable auto purchase workflow with purchase order confirmation. Include operations like Auto Create Supplier Bill, Auto Create Bill and Auto Transfer Delivery Order.""",
    'website': 'https://site.basic-powered.com',
    'license': 'OPL-1',
    'depends' : ['purchase_stock'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
}
