# -*- coding: utf-8 -*-
{
    'name': 'Limited Contacts by Salesperson (Palmalube)',
    'summary': 'Limita la visualización de contactos a los asignados al comercial (user_id) para usuarios del grupo Palmalube',
    'version': '18.0.1.0.0',
    'author': 'Palmalube / Adaptado por desarrollador',
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
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

