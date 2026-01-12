# -*- coding: utf-8 -*-
{
    'name': 'Limited Contacts by Salesperson (Palmalube)',
    'summary': '''Limita la visualización de contactos a los asignados al comercial.
        Comerciales ven: 1) sus contactos (user_id = ellos), 2) contactos de usuarios del sistema.
        Administradores y managers ven todos los contactos sin restricción.''',
    'version': '18.0.5.0.0',  # Solución final: regla res.users + res.partner
    'author': 'Xtendoo',
    'license': 'OPL-1',
    'category': 'Contacts',
    'depends': [
        'base',
        'contacts',
        'sales_team',
    ],
    'data': [
        'security/limited_contacts_security.xml',
        'security/ir.model.access.csv',
        'views/res_users_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
