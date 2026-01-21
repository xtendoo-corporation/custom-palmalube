from odoo import api, fields, models
from odoo.tools.translate import _
import re


def _strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]*>', '', text).strip()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Intentar obtener order_id de defaults/context
        order_id = res.get('order_id') or self._context.get('default_order_id')
        if order_id:
            order = self.env['sale.order'].browse(order_id)
            fsm = order.fsm_order_id if order else False
            if fsm:
                if 'equipo_ids' in fields_list:
                    res['equipo_ids'] = [(6, 0, fsm.equipment_ids.ids)]
                if 'intervencion' in fields_list:
                    text = ''
                    if getattr(fsm, 'internal_notes', False):
                        text = fsm.internal_notes
                    elif getattr(fsm, 'description', False):
                        text = fsm.description
                    res['intervencion'] = _strip_html(text)
        return res

    @api.onchange('order_id')
    def _onchange_order_id_fill_fsm(self):
        for line in self:
            order = line.order_id
            if not order:
                continue
            fsm = order.fsm_order_id
            if not fsm:
                continue
            # Rellenar equipo_ids si está vacío
            if not line.equipo_ids and fsm.equipment_ids:
                line.equipo_ids = [(6, 0, fsm.equipment_ids.ids)]
            # Rellenar intervencion si está vacío
            if not line.intervencion:
                text = fsm.internal_notes if getattr(fsm, 'internal_notes', False) else getattr(fsm, 'description', '')
                line.intervencion = _strip_html(text)
