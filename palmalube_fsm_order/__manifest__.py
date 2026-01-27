{
    'name': 'Palmalube FSM Order',
    'version': '18.0.1.0.0',
    'category': 'Custom',
    'summary': 'Extensión FSM Order con equipos',
    'author': 'Abraham, Xtendoo',
    'depends': [
        'xtendoo_fsm',
        'maintenance',
        'survey',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fsm_order_views.xml',
        'views/fsm_order_equipment_line_views.xml',
    ],
    'installable': True,
    'application': False,
}
