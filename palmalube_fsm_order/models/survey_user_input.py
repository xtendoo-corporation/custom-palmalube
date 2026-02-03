# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    fsm_order_equipment_line_id = fields.Many2one(
        "fsm.order.equipment.line",
        string="Línea de Equipo FSM",
        ondelete="cascade",
        help="Línea de equipo vinculada a esta respuesta de encuesta",
    )
    fsm_order_id = fields.Many2one(
        "fsm.order",
        string="Orden FSM",
        ondelete="cascade",
    )
    next_maintenance_date = fields.Date(
        string="Próxima Revisión",
        related="fsm_order_id.next_maintenance_date",
        readonly=True,
        store=True,
        help="Fecha de la próxima revisión/mantenimiento",
    )
    fsm_order_amount_total = fields.Monetary(
        string="Precio",
        related="fsm_order_id.amount_total",
        readonly=True,
        store=True,
        currency_field="fsm_order_currency_id",
        help="Importe total de la orden FSM",
    )
    fsm_order_currency_id = fields.Many2one(
        "res.currency",
        related="fsm_order_id.company_currency_id",
        readonly=True,
        store=True,
    )

    def write(self, vals):
        """Forzar recomputación de survey_state cuando cambia el estado de la encuesta."""
        result = super().write(vals)
        if 'state' in vals:
            # Obtener las líneas de equipo vinculadas
            lines = self.filtered(lambda r: r.fsm_order_equipment_line_id).mapped('fsm_order_equipment_line_id')
            if lines:
                # Forzar recomputación del campo survey_state
                lines._compute_survey_state()
                # Publicar mensaje si se completó
                if vals['state'] == 'done':
                    for line in lines:
                        line.fsm_order_id.message_post(
                            body=_("Encuesta completada para el equipo: %s") % line.equipment_id.name,
                            message_type="notification",
                        )
        return result
