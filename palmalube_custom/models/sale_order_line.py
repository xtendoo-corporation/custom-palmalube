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
    )  # Editable y con valor sugerido

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


    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        # Sugerir valor por defecto solo si se está creando desde un pedido
        order_id = self._context.get('default_order_id')
        if 'intervencion' in fields and order_id:
            order = self.env['sale.order'].browse(order_id)
            fsm_orders = self._get_fsm_orders_from_sale_order(order)
            for fsm_order in fsm_orders:
                if hasattr(fsm_order, 'description') and fsm_order.description:
                    res['intervencion'] = fsm_order.description
                    break
        return res

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

    def action_confirm_qty(self):
        """
        Actualiza la cantidad real (stock) del producto a la cantidad solicitada en la línea.
        Ajusta el inventario en la ubicación del almacén correspondiente.
        """
        self.ensure_one()

        if not self.product_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'No hay producto en esta línea.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        if self.product_id.type not in ['product', 'consu']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Advertencia',
                    'message': f'El producto {self.product_id.name} no es almacenable.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Obtener el almacén y la ubicación de stock
        warehouse = self.order_id.warehouse_id or self.env['stock.warehouse'].search([
            ('company_id', '=', self.order_id.company_id.id)
        ], limit=1)

        if not warehouse:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'No se encontró un almacén para esta orden.',
                    'type': 'danger',
                    'sticky': False,
                }
            }

        location = warehouse.lot_stock_id
        qty_needed = self.product_uom_qty

        # Obtener la cantidad actual en stock
        quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', location.id),
        ], limit=1)

        current_qty = quant.quantity if quant else 0.0

        # Calcular la diferencia
        qty_diff = qty_needed - current_qty

        # Actualizar el inventario
        self.env['stock.quant']._update_available_quantity(
            self.product_id,
            location,
            qty_diff
        )

        # Commit para asegurar que el cambio de stock se persiste
        self.env.cr.commit()

        # Forzar recálculo de campos de stock en todas las líneas del pedido
        if hasattr(self.order_id.order_line, '_compute_qty_at_date'):
            self.order_id.order_line._compute_qty_at_date()

        # Invalidar la caché para forzar recálculo de campos relacionados con stock
        self.order_id.order_line.invalidate_recordset([
            'qty_available_today',
            'free_qty_today',
            'virtual_available_at_date',
            'forecast_expected_date',
            'display_qty_widget'
        ])

        # Forzar recarga de la orden completa
        self.order_id.invalidate_recordset()

        # Retornar acción simple para recargar la vista
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'notification': {
                    'type': 'success',
                    'title': 'Stock actualizado',
                    'message': f'Stock de {self.product_id.name} actualizado de {current_qty:.2f} a {qty_needed:.2f} unidades.',
                }
            }
        }
