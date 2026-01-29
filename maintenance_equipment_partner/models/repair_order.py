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

    def action_create_sale_order(self):
        # Lógica igual que en la herencia FSM: asignar tipo de venta 'Reparacion' al presupuesto
        if any(repair.sale_order_id for repair in self):
            concerned_ro = self.filtered('sale_order_id')
            ref_str = "\n".join(ro.name for ro in concerned_ro)
            raise self.env['res.users'].browse(self.env.uid).sudo()._get_exception_class()( # UserError
                "No puedes crear un presupuesto para una orden de reparación ya vinculada a un pedido de venta.\nÓrdenes afectadas:\n%s" % ref_str
            )
        if any(not repair.partner_id for repair in self):
            concerned_ro = self.filtered(lambda ro: not ro.partner_id)
            ref_str = "\n".join(ro.name for ro in concerned_ro)
            raise self.env['res.users'].browse(self.env.uid).sudo()._get_exception_class()( # UserError
                "Debes definir un cliente para la orden de reparación para crear el presupuesto asociado.\nÓrdenes afectadas:\n%s" % ref_str
            )
        sale_order_values_list = []
        type_id = self.env.ref('palmalube_sale_type.sale_order_type_reparacion', raise_if_not_found=False)
        for repair in self:
            vals = {
                "company_id": repair.company_id.id,
                "partner_id": repair.partner_id.id,
                "warehouse_id": repair.picking_type_id.warehouse_id.id,
                "repair_order_ids": [(4, repair.id)],
            }
            if type_id:
                vals["type_id"] = type_id.id
            sale_order = self.env['sale.order'].create(vals)
            # Relacionar la orden de reparación con el pedido de venta
            repair.sale_order_id = sale_order.id
        # Crear líneas de venta a partir de los movimientos de stock
        self.move_ids._create_repair_sale_order_line()
        return self.action_view_sale_order()
