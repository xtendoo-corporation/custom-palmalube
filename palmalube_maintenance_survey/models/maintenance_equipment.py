# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    default_survey_id = fields.Many2one(
        "survey.survey",
        string="Encuesta de mantenimiento por defecto",
        help="Encuesta que se asignará automáticamente al crear una solicitud de mantenimiento para este equipo.",
    )
