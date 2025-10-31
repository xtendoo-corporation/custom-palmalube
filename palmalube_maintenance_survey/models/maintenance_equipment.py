# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    default_survey_id = fields.Many2one(
        "survey.survey",
        string="Default Post-Service Survey",
        help="This survey will be automatically assigned to new maintenance "
        "requests for this equipment",
    )

