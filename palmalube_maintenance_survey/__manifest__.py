# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Palmalube Maintenance Survey",
    "version": "18.0.1.1.0",
    "category": "Maintenance",
    "summary": "Link maintenance requests with surveys for post-service quality control",
    "author": "Palmalube",
    "website": "https://github.com/palmalube/custom-palmalube",
    "license": "AGPL-3",
    "depends": [
        "maintenance",
        "survey",
        "mail",
        "palmalube_fsm_order",
    ],
    "data": [
        "security/ir.model.access.csv",
        # "views/maintenance_request_views.xml",
        "views/maintenance_stage_views.xml",
        "views/maintenance_equipment_views.xml",
        "data/maintenance_survey_demo.xml",
        "views/survey_templates.xml",
        "views/survey_user_input_answers_inherit.xml",
    ],
    "demo": [
        "data/maintenance_survey_demo.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
