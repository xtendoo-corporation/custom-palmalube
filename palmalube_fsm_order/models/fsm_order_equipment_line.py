# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class FSMOrderEquipmentLine(models.Model):
    _name = "fsm.order.equipment.line"
    _description = "Línea de Equipo en Orden FSM"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)
    fsm_order_id = fields.Many2one(
        "fsm.order",
        string="Orden FSM",
        required=True,
        ondelete="cascade",
    )
    equipment_id = fields.Many2one(
        "maintenance.equipment",
        string="Equipo",
        required=True,
    )

    # Campos relacionados con la encuesta
    survey_id = fields.Many2one(
        "survey.survey",
        string="Encuesta",
        help="Encuesta asignada a este equipo",
    )
    survey_user_input_id = fields.Many2one(
        "survey.user_input",
        string="Respuesta de Encuesta",
        readonly=True,
        copy=False,
    )
    survey_state = fields.Selection(
        [
            ("not_started", "No Iniciada"),
            ("in_progress", "En Progreso"),
            ("completed", "Completada"),
        ],
        string="Estado Encuesta",
        compute="_compute_survey_state",
        store=True,
        default="not_started",
    )

    # Campos informativos del equipo
    equipment_category_id = fields.Many2one(
        related="equipment_id.category_id",
        string="Categoría",
        readonly=True,
    )
    equipment_partner_id = fields.Many2one(
        related="equipment_id.customer_id",
        string="Cliente del Equipo",
        readonly=True,
    )

    @api.depends("survey_user_input_id", "survey_user_input_id.state")
    def _compute_survey_state(self):
        """Calcular estado de la encuesta basado en la respuesta."""
        for line in self:
            if not line.survey_user_input_id:
                line.survey_state = "not_started"
            elif line.survey_user_input_id.state == "done":
                line.survey_state = "completed"
            elif line.survey_user_input_id.state in ("new", "in_progress"):
                line.survey_state = "in_progress"
            else:
                line.survey_state = "not_started"

    @api.onchange("equipment_id")
    def _onchange_equipment_id(self):
        """Auto-asignar encuesta desde el equipo si existe."""
        if self.equipment_id and self.equipment_id.default_survey_id:
            self.survey_id = self.equipment_id.default_survey_id

    def action_start_survey(self):
        """Iniciar la encuesta para este equipo específico."""
        self.ensure_one()

        if not self.survey_id:
            raise UserError(_("No hay encuesta asignada a este equipo."))

        # Obtener el partner del usuario actual
        current_user = self.env.user
        if not current_user._is_public():
            partner_id = current_user.partner_id.id
        else:
            partner_id = False
            # Si es público, intentar obtener del responsable o cliente
            if self.fsm_order_id.responsible_id and self.fsm_order_id.responsible_id.user_id:
                partner_id = self.fsm_order_id.responsible_id.user_id.partner_id.id
            elif self.fsm_order_id.partner_id:
                partner_id = self.fsm_order_id.partner_id.id

        # Buscar o crear el registro de respuesta
        user_input = self.env["survey.user_input"].search([
            ("survey_id", "=", self.survey_id.id),
            ("fsm_order_equipment_line_id", "=", self.id),
        ], limit=1)

        if not user_input:
            user_input = self.env["survey.user_input"].sudo().create({
                "survey_id": self.survey_id.id,
                "partner_id": partner_id,
                "fsm_order_id": self.fsm_order_id.id,
                "fsm_order_equipment_line_id": self.id,
            })
        else:
            # Si ya existe, actualizar el partner_id para que coincida con el usuario actual
            if user_input.partner_id.id != partner_id:
                user_input.sudo().write({'partner_id': partner_id})

        # Siempre asignar el user_input a la línea
        if self.survey_user_input_id != user_input:
            self.write({'survey_user_input_id': user_input.id})

        # Abrir la encuesta pasando el answer correctamente
        return self.survey_id.action_start_survey(answer=user_input)

    def action_view_survey_result(self):
        """Ver el resultado de la encuesta de este equipo."""
        self.ensure_one()

        if not self.survey_user_input_id:
            raise UserError(_("No hay respuesta de encuesta para este equipo."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Resultado de Encuesta"),
            "res_model": "survey.user_input",
            "res_id": self.survey_user_input_id.id,
            "view_mode": "form",
            "target": "current",
        }
