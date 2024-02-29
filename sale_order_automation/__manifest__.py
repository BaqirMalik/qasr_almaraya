{
    'name' : 'Sale Order Automation',
    'version' : '1.0',
    'author':'AliFaleh@BasicPowered',
    'category': 'Sales',
    'summary': """Enable auto sale workflow with sale order confirmation. Include operations like Auto Create Invoice, Auto Validate Invoice and Auto Transfer Delivery Order.""",
    'description': """

        You can directly create invoice and set done to delivery order by single click

    """,
    'website': 'https://site.basic-powered.com',
    'license': 'LGPL-3',
    'depends' : ['sale_management','stock','sale_stock'],
    'data': [
        'views/stock_warehouse.xml',
    ],
    'installable': True,
}
