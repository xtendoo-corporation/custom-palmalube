{
    'name': 'Partner Salesperson Import Helper',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Importa comerciales a clientes desde Excel',
    'author': 'Ivan Parrado',
    'website': 'https://xtendoo.es',
    'depends': ['base', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/partner_salesperson_import_wizard_view.xml',
        'wizard/partner_contact_address_import_wizard_view.xml',
        'views/partner_salesperson_import_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
