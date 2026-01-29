# -*- coding: utf-8 -*-
from odoo import models, api, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    type_id = fields.Many2one(
        'sale.order.type',
        string='Type',
        required=False,
    )

    @api.onchange('type_id')
    def _onchange_sale_type_id_set_journal(self):
        """
        Al cambiar el tipo de venta, asigna el diario correspondiente si está definido en el tipo.
        """
        if self.type_id and self.type_id.journal_id:
            self.journal_id = self.type_id.journal_id.id

    @api.model
    def create(self, vals):
        # Al crear, asignar el diario si el tipo de venta lo tiene definido
        if vals.get('type_id'):
            sale_type = self.env['sale.order.type'].browse(vals['type_id'])
            if sale_type.journal_id:
                vals['journal_id'] = sale_type.journal_id.id
        return super().create(vals)
