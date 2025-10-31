# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MaintenanceStage(models.Model):
    _inherit = "maintenance.stage"

    require_survey = fields.Boolean(
        string="Require Survey",
        default=False,
        help="If checked, maintenance requests in this stage must complete "
        "the assigned survey before moving to another stage",
    )

