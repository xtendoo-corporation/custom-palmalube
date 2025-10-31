# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    survey_id = fields.Many2one(
        "survey.survey",
        string="Post-Service Survey",
        help="Survey to be completed after maintenance service",
        tracking=True,
    )
    survey_user_input_id = fields.Many2one(
        "survey.user_input",
        string="Survey Response",
        readonly=True,
        copy=False,
        help="Survey response submitted by the technician",
    )
    survey_state = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        string="Survey Status",
        compute="_compute_survey_state",
        store=True,
        default="not_started",
        help="Status of the post-service survey",
    )
    survey_required = fields.Boolean(
        string="Survey Required",
        compute="_compute_survey_required",
        store=True,
        help="True if survey must be completed before closing this request",
    )
    survey_count = fields.Integer(
        string="Survey Count",
        compute="_compute_survey_count",
    )

    @api.depends("survey_id", "stage_id", "stage_id.require_survey")
    def _compute_survey_required(self):
        """Survey is required when stage requires it and survey is assigned."""
        for request in self:
            request.survey_required = bool(
                request.survey_id and request.stage_id.require_survey
            )

    @api.depends("survey_user_input_id", "survey_user_input_id.state")
    def _compute_survey_state(self):
        """Compute survey state based on user input state."""
        for request in self:
            if not request.survey_user_input_id:
                request.survey_state = "not_started"
            elif request.survey_user_input_id.state == "done":
                request.survey_state = "completed"
            elif request.survey_user_input_id.state in ("new", "in_progress"):
                request.survey_state = "in_progress"
            else:
                request.survey_state = "failed"

    @api.depends("survey_user_input_id")
    def _compute_survey_count(self):
        """Count survey responses."""
        for request in self:
            request.survey_count = 1 if request.survey_user_input_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-fill survey from equipment default if not provided."""
        for vals in vals_list:
            if vals.get("equipment_id") and not vals.get("survey_id"):
                equipment = self.env["maintenance.equipment"].browse(
                    vals["equipment_id"]
                )
                if equipment.default_survey_id:
                    vals["survey_id"] = equipment.default_survey_id.id
        return super().create(vals_list)

    def write(self, vals):
        """Prevent closing request if survey is required but not completed."""
        # Check if stage is being changed
        if "stage_id" in vals:
            new_stage = self.env["maintenance.stage"].browse(vals["stage_id"])
            for request in self:
                # If moving to a stage that requires survey
                if new_stage.require_survey:
                    if request.survey_id and request.survey_state != "completed":
                        raise UserError(
                            _(
                                "Cannot move to stage '%(stage)s' because "
                                "the post-service survey is required but not completed.\n"
                                "Please complete the survey first.",
                                stage=new_stage.name,
                            )
                        )
        return super().write(vals)

    def action_start_survey(self):
        """Create or open survey user input for this maintenance request."""
        self.ensure_one()

        if not self.survey_id:
            raise UserError(_("No survey assigned to this maintenance request."))

        # Check if survey input already exists
        if self.survey_user_input_id:
            user_input = self.survey_user_input_id
        else:
            # Create new survey user input
            partner_id = False
            if self.user_id:
                partner_id = self.user_id.partner_id.id
            elif self.owner_user_id:
                partner_id = self.owner_user_id.partner_id.id

            user_input = self.env["survey.user_input"].create(
                {
                    "survey_id": self.survey_id.id,
                    "partner_id": partner_id,
                    "maintenance_request_id": self.id,
                }
            )
            self.survey_user_input_id = user_input.id

        # Send notification
        self.message_post(
            body=_("Survey started by %s", self.env.user.name),
            message_type="notification",
        )

        # Return action to open survey
        return {
            "type": "ir.actions.act_window",
            "name": _("Complete Survey: %s", self.survey_id.title),
            "res_model": "survey.user_input",
            "res_id": user_input.id,
            "view_mode": "form",
            "target": "current",
            "context": {"form_view_initial_mode": "edit"},
        }

    def action_view_survey_result(self):
        """Open survey response."""
        self.ensure_one()

        if not self.survey_user_input_id:
            raise UserError(_("No survey response found for this maintenance request."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Survey Response"),
            "res_model": "survey.user_input",
            "res_id": self.survey_user_input_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.onchange("stage_id")
    def _onchange_stage_id(self):
        """Send notification when moving to stage that requires survey."""
        if self.stage_id and self.stage_id.require_survey and self.survey_id:
            if self.survey_state != "completed":
                # Notify assigned user
                if self.user_id:
                    self.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=self.user_id.id,
                        summary=_("Complete Post-Service Survey"),
                        note=_(
                            "Please complete the survey for maintenance request: %s",
                            self.name,
                        ),
                    )

