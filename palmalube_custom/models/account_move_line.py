from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    equipo_ids = fields.Many2many(
        'maintenance.equipment',
        string='Equipos',
        domain="[('id', 'in', equipo_domain_ids)]"
    )
    intervencion = fields.Char(string='Intervención')
    equipo_domain_ids = fields.Many2many(
        'maintenance.equipment',
        compute='_compute_equipo_domain_ids',
        string='Equipos dominio',
        store=False
    )

    @api.depends('move_id', 'sale_line_ids')
    def _compute_equipo_domain_ids(self):
        for line in self:
            equipos_ids = []
            sale_line = line.sale_line_ids[:1] if line.sale_line_ids else False
            if sale_line:
                equipos_ids = sale_line.equipo_ids.ids
            line.equipo_domain_ids = equipos_ids

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Propagar valores por defecto desde la línea de venta
            if vals.get('sale_line_ids'):
                sale_line = self.env['sale.order.line'].browse(vals['sale_line_ids'][0][1])
                if sale_line:
                    vals.setdefault('equipo_ids', [(6, 0, sale_line.equipo_ids.ids)])
                    vals.setdefault('intervencion', sale_line.intervencion)
        return super().create(vals_list)

    def write(self, vals):
        # Si se cambia la relación con la línea de venta, actualizar valores
        if 'sale_line_ids' in vals:
            for line in self:
                sale_line = self.env['sale.order.line'].browse(vals['sale_line_ids'][0][1]) if vals['sale_line_ids'] else False
                if sale_line:
                    vals.setdefault('equipo_ids', [(6, 0, sale_line.equipo_ids.ids)])
                    vals.setdefault('intervencion', sale_line.intervencion)
        return super().write(vals)
