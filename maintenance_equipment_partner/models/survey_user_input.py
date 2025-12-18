# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    maintenance_request_equipment_line_id = fields.Many2one(
        "maintenance.request.equipment.line",
        string="Línea de Equipo",
        ondelete="cascade",
        help="Línea de equipo vinculada a esta respuesta de encuesta",
    )
    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="Solicitud de Mantenimiento",
        ondelete="cascade",
    )

    def write(self, vals):
        """Forzar recomputación de survey_state cuando cambia el estado de la encuesta."""
        result = super().write(vals)
        if 'state' in vals:
            # Obtener las líneas de equipo vinculadas
            lines = self.filtered(lambda r: r.maintenance_request_equipment_line_id).mapped('maintenance_request_equipment_line_id')
            if lines:
                # Forzar recomputación del campo survey_state
                lines._compute_survey_state()
                # Publicar mensaje si se completó
                if vals['state'] == 'done':
                    for line in lines:
                        line.request_id.message_post(
                            body=_("Encuesta completada para el equipo: %s") % line.equipment_id.name,
                            message_type="notification",
                        )
        return result

