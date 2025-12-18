# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Maintenance Equipment Partner",
    "summary": "Añade relación con cliente en equipos de mantenimiento",
    "version": "18.0.2.11.0",
    "category": "Maintenance",
    "website": "https://github.com/xtendoo-corporation/custom-palmalube",
    "author": "Ivan Parrado, Manuel Calero, Xtendoo SLU",
    "license": "AGPL-3",
    "depends": [
        "maintenance",
        "repair",
        "survey",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "data/ir_cron_data.xml",
        "views/maintenance_equipment_views.xml",
        "views/res_partner_views.xml",
        "views/maintenance_request_equipment_line_views.xml",
        "views/maintenance_request_views.xml",
    ],
    "installable": True,
    "application": False,
}
