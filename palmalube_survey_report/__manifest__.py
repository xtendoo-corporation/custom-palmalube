# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Palmalube Survey Report",
    "version": "18.0.1.0.0",
    "category": "Survey",
    "summary": "Print survey responses in table format",
    "author": "Palmalube",
    "website": "https://github.com/palmalube/custom-palmalube",
    "license": "AGPL-3",
    "depends": [
        "survey",
        "web",
        "palmalube_maintenance_survey",
    ],
    "data": [
        "report/survey_user_input_report.xml",
        "report/survey_user_input_templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
