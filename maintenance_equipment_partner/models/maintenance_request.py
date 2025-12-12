# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api

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
