from odoo import _, api, fields, models

class FSMOrder(models.Model):
    _inherit = 'fsm.order'

    equipment_ids = fields.Many2many(
        'maintenance.equipment',
        string='Equipos',
        domain="[('customer_id', '=', partner_id)]"
    )


    @api.onchange('partner_id')
    def _onchange_partner_id_equipment_ids(self):
        if self.partner_id:
            # Limpiar equipos que no correspondan al cliente seleccionado
            equipos_validos = self.equipment_ids.filtered(lambda eq: eq.customer_id == self.partner_id)
            self.equipment_ids = equipos_validos
            domain = [('customer_id', '=', self.partner_id.id)]
            return {'domain': {'equipment_ids': domain}}
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

    def action_open_sale_order(self):
        """Abre la orden de venta relacionada desde la FSM Order."""
        self.ensure_one()
        if not self.sale_order_ids:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Venta',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_ids.id,
            'target': 'current',
        }

    def action_create_sale_order(self):
        """Crea una orden de venta basada en la orden de trabajo"""
        print("[FSMOrder] action_create_sale_order called for FSM Order ID:", self.id)
        self.ensure_one()
        sale_order_vals = {
            'partner_id': self.partner_id.id,
            'fsm_order_id': self.id,  # Relaciona la orden de venta con el fsm.order
        }
        print("[FSMOrder] Valores para crear sale.order:", sale_order_vals)
        sale_order = self.env['sale.order'].create(sale_order_vals)
        print("[FSMOrder] Sale Order creado con ID:", sale_order.id)
        # Crear líneas de venta a partir de los movimientos de stock
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Venta'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'view_id': self.env.ref('sale.view_order_form').id,
            'target': 'current',
        }


