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

    # NOTA: Se eliminó la restricción SQL 'maintenance_request_survey_unique'
    # porque ahora permitimos múltiples encuestas del mismo tipo en un mantenimiento
    # (una por cada línea de equipo)

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
                        body="Encuesta completada por %s" % self.env.user.name,
                        message_type="notification",
                    )

        # Si el registro está vinculado y se marca como completado, asegurar el vínculo
        for user_input in self.filtered('maintenance_request_id'):
            if user_input.maintenance_request_id.survey_user_input_id != user_input:
                user_input.maintenance_request_id.sudo().write({'survey_user_input_id': user_input.id})

        return res

    def action_view_results(self):
        self.ensure_one()
        if self.maintenance_request_id:
            return {
                'type': 'ir.actions.act_window',
                'id': self.env.ref('maintenance.action_maintenance_request').id,
                'res_model': 'survey.user_input',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'active_id': self.maintenance_request_id.id,
                    'active_model': 'maintenance.request',
                },
            }
        # Si no hay solicitud vinculada, mostrar la vista normal
        return {
            'type': 'ir.actions.act_window',
            'name': 'Resultados de la Encuesta',
            'res_model': 'survey.user_input',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def create(self, vals):
        survey_id = vals.get('survey_id')
        maintenance_request_id = vals.get('maintenance_request_id')
        maintenance_request_equipment_line_id = vals.get('maintenance_request_equipment_line_id')
        ctx = self.env.context

        # Si no hay maintenance_request_id, intentar vincularlo por contexto o por búsqueda
        if not maintenance_request_id:
            # Intentar contexto
            if ctx.get('active_model') == 'maintenance.request' and ctx.get('active_id'):
                vals['maintenance_request_id'] = ctx['active_id']
                maintenance_request_id = vals['maintenance_request_id']
            # Si sigue sin estar, buscar el mantenimiento por usuario y survey
            elif survey_id:
                # Buscar el mantenimiento más reciente con ese survey y estado abierto
                request = self.env['maintenance.request'].search([
                    ('survey_id', '=', survey_id),
                    ('stage_id', '!=', False),
                ], order='id desc', limit=1)
                if request:
                    vals['maintenance_request_id'] = request.id
                    maintenance_request_id = request.id

        # Si existe un registro para la combinación, reutilizarlo
        # IMPORTANTE: Si hay maintenance_request_equipment_line_id, verificarlo también
        # para que cada línea tenga su propia encuesta independiente
        if survey_id and maintenance_request_id:
            domain = [
                ('survey_id', '=', survey_id),
                ('maintenance_request_id', '=', maintenance_request_id)
            ]
            # Si es de una línea específica, buscar solo esa combinación
            if maintenance_request_equipment_line_id:
                domain.append(('maintenance_request_equipment_line_id', '=', maintenance_request_equipment_line_id))
            else:
                # Si no es de una línea, asegurar que no tenga línea asociada
                domain.append(('maintenance_request_equipment_line_id', '=', False))

            existing = self.env['survey.user_input'].search(domain, limit=1)
            if existing:
                existing.sudo().write(vals)
                return existing

        record = super().create(vals)
        if record.maintenance_request_id:
            record.maintenance_request_id.sudo().write({'survey_user_input_id': record.id})
        return record

