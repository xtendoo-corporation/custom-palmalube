# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


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
                # Invalidar caché y forzar recomputación
                self.env.add_to_compute(
                    self.env['maintenance.request.equipment.line']._fields['survey_state'],
                    lines
                )
        return result

