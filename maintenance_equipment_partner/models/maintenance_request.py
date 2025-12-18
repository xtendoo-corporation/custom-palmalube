# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import timedelta

class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    repair_order_id = fields.Many2one("repair.order", "Orden de reparación")
    partner_id = fields.Many2one(
        "res.partner", string="Cliente",
        help="Cliente al que se le realiza el mantenimiento.")
    equipment_ids = fields.Many2many(
        "maintenance.equipment",
        string="Equipos",
        help="Equipos asociados a esta solicitud de mantenimiento"
    )
    equipment_line_ids = fields.One2many(
        "maintenance.request.equipment.line",
        "request_id",
        string="Líneas de Equipos",
        help="Equipos con sus encuestas individuales"
    )
    equipment_count = fields.Integer(
        string="Número de Equipos",
        compute="_compute_equipment_count",
        store=True,
    )
    reminder_sent = fields.Boolean(
        string="Recordatorio Enviado",
        default=False,
        copy=False,
        help="Indica si ya se envió el recordatorio de 15 días antes del mantenimiento"
    )

    @api.depends('equipment_line_ids')
    def _compute_equipment_count(self):
        """Contar el número de equipos en las líneas."""
        for request in self:
            request.equipment_count = len(request.equipment_line_ids)

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        """Sincronizar equipment_id con equipment_line_ids"""
        if self.equipment_id:
            # Verificar si ya existe en las líneas
            existing_line = self.equipment_line_ids.filtered(
                lambda l: l.equipment_id == self.equipment_id
            )
            if not existing_line:
                # Agregar nueva línea
                self.equipment_line_ids = [(0, 0, {
                    'equipment_id': self.equipment_id.id,
                    'survey_id': self.equipment_id.default_survey_id.id if self.equipment_id.default_survey_id else False,
                })]

    @api.onchange('equipment_line_ids')
    def _onchange_equipment_line_ids(self):
        """Sincronizar equipment_line_ids con equipment_id (tomar el primero)"""
        if self.equipment_line_ids:
            # Actualizar equipment_ids (Many2many) desde las líneas
            equipment_ids = self.equipment_line_ids.mapped('equipment_id')
            self.equipment_ids = [(6, 0, equipment_ids.ids)]
            # Sincronizar equipment_id con el primero de la lista
            if not self.equipment_id or self.equipment_id not in equipment_ids:
                self.equipment_id = equipment_ids[0] if equipment_ids else False
        else:
            self.equipment_ids = [(5, 0, 0)]
            self.equipment_id = False

    def action_create_repair_order(self):
        self.ensure_one()
        # Si hay múltiples equipos, tomar el primero para la orden de reparación
        equipment_id = self.equipment_ids[0].id if self.equipment_ids else (self.equipment_id.id if self.equipment_id else False)
        repair = self.env['repair.order'].create({
            'maintenance_request_ids': [(4, self.id)],
            'partner_id': self.partner_id.id if self.partner_id else False,
            'equipment_id': equipment_id,
        })
        self.repair_order_id = repair.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'view_mode': 'form',
            'res_id': repair.id,
            'target': 'current',
        }

    def action_open_repair_order(self):
        self.ensure_one()
        if not self.repair_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'view_mode': 'form',
            'res_id': self.repair_order_id.id,
            'target': 'current',
        }

    def _send_maintenance_reminder(self):
        """Enviar recordatorio de mantenimiento al cliente."""
        self.ensure_one()
        if not self.partner_id or not self.partner_id.email:
            return False

        template = self.env.ref(
            'maintenance_equipment_partner.email_template_maintenance_reminder',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)
            self.reminder_sent = True
            return True
        return False

    @api.model
    def _cron_send_maintenance_reminders(self):
        """Acción programada para enviar recordatorios de mantenimiento."""
        today = fields.Date.today()
        reminder_date = today + timedelta(days=15)

        # Buscar mantenimientos programados para dentro de 15 días
        # que aún no han enviado recordatorio y tienen cliente asignado
        maintenance_requests = self.search([
            ('schedule_date', '>=', fields.Datetime.to_datetime(reminder_date)),
            ('schedule_date', '<', fields.Datetime.to_datetime(reminder_date + timedelta(days=1))),
            ('reminder_sent', '=', False),
            ('partner_id', '!=', False),
            ('stage_id.done', '=', False),  # No enviar si ya está completado
        ])

        for request in maintenance_requests:
            try:
                request._send_maintenance_reminder()
            except Exception as e:
                # Log del error pero continuar con los demás
                self.env['ir.logging'].sudo().create({
                    'name': 'Maintenance Reminder Error',
                    'type': 'server',
                    'level': 'ERROR',
                    'message': f'Error al enviar recordatorio para mantenimiento {request.id}: {str(e)}',
                    'path': 'maintenance.request',
                    'func': '_cron_send_maintenance_reminders',
                })
                continue

        return True

