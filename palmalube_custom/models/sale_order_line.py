from odoo import models, fields, api
import logging

logger = logging.getLogger(__name__)
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

    def _empty_fsm(self):
        return self.env['fsm.order'].browse(self.env['fsm.order'].ids[:0])

    def _get_fsm_orders_from_sale_order(self, sale_order):
        """Devuelve recordset de fsm.order relacionados con la sale.order de forma segura.
        Comprueba distintas posibles relaciones y evita hacer domains sobre campos inexistentes.
        Retorna un recordset (posiblemente vacío).
        """
        if not sale_order:
            return self._empty_fsm()
        # 1) Si sale.order tiene un campo many2one hacia fsm.order (fsm_order_id)
        if 'fsm_order_id' in sale_order._fields:
            fsm = getattr(sale_order, 'fsm_order_id')
            return fsm if fsm else self._empty_fsm()
        # 2) Si sale.order tiene un campo one2many/many2many hacia fsm.order (fsm_order_ids)
        if 'fsm_order_ids' in sale_order._fields:
            return getattr(sale_order, 'fsm_order_ids') or self._empty_fsm()
        # 3) Buscar en el modelo fsm.order si existe un campo que apunte a sale.order sin lanzar error
        fsm_model = self.env['fsm.order']
        candidate_fields = ['sale_order_id', 'sale_order_ids', 'order_id', 'sale_order']
        for fname in candidate_fields:
            if fname in fsm_model._fields:
                # safe search: ensure field is valid for domain
                try:
                    # Only build simple equality domain on existing field names
                    return fsm_model.search([(fname, '=', sale_order.id)])
                except Exception:
                    continue
        # 4) fallback: empty recordset
        return self._empty_fsm()

    @api.depends('order_id')
    def _compute_equipo_domain_ids(self):
        for line in self:
            equipos_ids = []
            if line.order_id:
                fsm_orders = self._get_fsm_orders_from_sale_order(line.order_id)
                if fsm_orders:
                    equipos_ids = fsm_orders.mapped('equipment_ids').ids
            # Assign as list of ids to a helper Many2many field via command
            line.equipo_domain_ids = [(6, 0, equipos_ids)]

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
                fsm_orders = self._get_fsm_orders_from_sale_order(line.order_id)
                if fsm_orders:
                    texts = []
                    for fsm in fsm_orders:
                        txt = False
                        if hasattr(fsm, 'description') and fsm.description:
                            txt = fsm.description
                        if txt:
                            clean = re.sub('<[^<]+?>', '', txt) if txt else ''
                            texts.append(clean.strip())
                    if texts:
                        intervencion = '\n'.join(texts)
            line.intervencion = intervencion

    @api.onchange('order_id')
    def _onchange_equipo_intervencion(self):
        for line in self:
            equipos = self.env['maintenance.equipment']
            intervencion = ''
            if not line.order_id:
                continue
            fsm_orders = self._get_fsm_orders_from_sale_order(line.order_id)
            for fsm_order in fsm_orders:
                if hasattr(fsm_order, 'equipment_ids') and fsm_order.equipment_ids:
                    equipos |= fsm_order.equipment_ids
                elif hasattr(fsm_order, 'description') and fsm_order.description:
                    intervencion = fsm_order.description
            # Si el campo está vacío, sugerir el valor
            if not line.equipo_ids and equipos:
                line.equipo_ids = equipos
            if not line.intervencion and intervencion:
                line.intervencion = intervencion

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_discount(self):
        discount_enabled = self.env['product.pricelist.item']._is_discount_feature_enabled()
        for line in self:
            if not line.product_id or line.display_type:
                line.discount = 0.0
                continue
            if not (line.order_id and line.order_id.pricelist_id and discount_enabled):
                continue
            if getattr(line, 'combo_item_id', None):
                linked_discount = line._get_linked_line().discount
                line.discount = linked_discount
                continue
            if not line.pricelist_item_id or not line.pricelist_item_id._show_discount():
                continue
            line.discount = 0.0
            line = line.with_company(line.company_id)
            pricelist_price = line._get_pricelist_price()
            base_price = line._get_pricelist_price_before_discount()
            if base_price != 0:  # Evitar división por cero
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (discount < 0 and base_price < 0):
                    line.discount = discount
