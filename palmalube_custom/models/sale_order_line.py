from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    equipo_ids = fields.Many2many(
        'maintenance.equipment',
        string='Equipos',
        domain="[('id', 'in', equipo_domain_ids)]"
    )  # Editable
    intervencion = fields.Char(
        string='Intervención',
        compute='_compute_intervencion',
        store=False
    )  # Editable

    @api.depends('order_id')
    def _compute_equipo_domain_ids(self):
        for line in self:
            equipos_ids = []
            if line.order_id:
                repair_orders = self.env['repair.order'].search([('sale_order_id', '=', line.order_id.id)])
                for repair_order in repair_orders:
                    if hasattr(repair_order, 'equipment_ids') and repair_order.equipment_ids:
                        equipos_ids += repair_order.equipment_ids.ids
            line.equipo_domain_ids = equipos_ids

    equipo_domain_ids = fields.Many2many(
        'maintenance.equipment',
        compute='_compute_equipo_domain_ids',
        string='Equipos dominio',
        store=False
    )

    @api.depends('order_id')
    def _compute_intervencion(self):
        import re
        for line in self:
            intervencion = ''
            if line.order_id:
                repair_orders = self.env['repair.order'].search([('sale_order_id', '=', line.order_id.id)])
                for repair_order in repair_orders:
                    if hasattr(repair_order, 'internal_notes') and repair_order.internal_notes:
                        # Extraer solo el texto plano de internal_notes (eliminar etiquetas HTML)
                        raw = repair_order.internal_notes
                        clean = re.sub('<[^<]+?>', '', raw) if raw else ''
                        intervencion = clean.strip()
            line.intervencion = intervencion

    @api.onchange('order_id')
    def _onchange_equipo_intervencion(self):
        for line in self:
            equipos = self.env['maintenance.equipment']
            intervencion = ''
            # Buscar repair.order relacionado
            repair_orders = self.env['repair.order'].search([('sale_order_id', '=', line.order_id.id)])
            for repair_order in repair_orders:
                if hasattr(repair_order, 'equipment_ids') and repair_order.equipment_ids:
                    equipos |= repair_order.equipment_ids
                if hasattr(repair_order, 'internal_notes') and repair_order.internal_notes:
                    intervencion = repair_order.internal_notes
            # Si el campo está vacío, sugerir el valor
            if not line.equipo_ids:
                line.equipo_ids = equipos
            if not line.intervencion:
                line.intervencion = intervencion
