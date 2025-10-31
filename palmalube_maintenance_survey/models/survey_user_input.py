# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="Maintenance Request",
        ondelete="cascade",
        help="Maintenance request linked to this survey response",
    )

    def write(self, vals):
        """Sync survey state to maintenance request when completed."""
        res = super().write(vals)

        # If state changed to 'done', update maintenance request
        if "state" in vals:
            for user_input in self.filtered("maintenance_request_id"):
                # Trigger recompute of survey_state in maintenance request
                user_input.maintenance_request_id._compute_survey_state()

                if vals["state"] == "done":
                    # Post message in maintenance request
                    user_input.maintenance_request_id.message_post(
                        body=_("Survey completed by %s", self.env.user.name),
                        message_type="notification",
                    )

        return res

