# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class RepairOrder(models.Model):
    _inherit = 'repair.order'

    # equipment_id = fields.Many2one('maintenance.equipment', string='Equipo')
    equipment_ids = fields.Many2many(
        'maintenance.equipment',
        string='Equipos',
        domain="[('customer_id', '=', partner_id)]"
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_equipment_ids(self):
        _logger.info('ONCHANGE partner_id: %s', self.partner_id)
        if self.partner_id:
            # Limpiar equipos que no correspondan al cliente seleccionado
            equipos_validos = self.equipment_ids.filtered(lambda eq: eq.customer_id == self.partner_id)
            if len(equipos_validos) != len(self.equipment_ids):
                _logger.info('Limpiando equipos no válidos para el cliente: %s', self.partner_id)
            self.equipment_ids = equipos_validos
            domain = [('customer_id', '=', self.partner_id.id)]
            return {'domain': {'equipment_ids': domain}}
        _logger.info('Sin partner_id, domain vacío para equipment_ids')
        self.equipment_ids = False
        return {'domain': {'equipment_ids': []}}

    @api.model
    def create(self, vals):
        if vals.get('partner_id') and vals.get('equipment_ids'):
            equipos = self.env['maintenance.equipment'].browse([e[1] for e in vals['equipment_ids'] if e[0] == 4])
            for eq in equipos:
                if eq.customer_id.id != vals['partner_id']:
                    raise ValueError('No puedes asignar equipos de otro cliente a esta reparación.')
        return super().create(vals)

    def write(self, vals):
        partner_id = vals.get('partner_id', self.partner_id.id)
        if 'equipment_ids' in vals:
            equipos = self.env['maintenance.equipment'].browse([e[1] for e in vals['equipment_ids'] if e[0] == 4])
            for eq in equipos:
                if eq.customer_id.id != partner_id:
                    raise ValueError('No puedes asignar equipos de otro cliente a esta reparación.')
        return super().write(vals)
