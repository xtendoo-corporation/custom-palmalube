from odoo import _, api, fields, models

class FSMOrder(models.Model):
    _inherit = 'fsm.order'
    _description = 'Mantenimiento'
    _order = 'name desc'

    equipment_ids = fields.Many2many(
        'maintenance.equipment',
        string='Equipos',
        domain="[('customer_id', '=', partner_id)]"
    )
    equipment_line_ids = fields.One2many(
        "fsm.order.equipment.line",
        "fsm_order_id",
        string="Líneas de Equipos",
        help="Equipos con sus encuestas individuales"
    )
    equipment_count = fields.Integer(
        string="Número de Equipos",
        compute="_compute_equipment_count",
        store=True,
    )
    date_open = fields.Datetime(
        string="Fecha de Apertura",
        related="create_date",
        store=True,
    )
    amount_total = fields.Monetary(
        string="Importe",
        compute="_compute_amount_total",
        currency_field="company_currency_id",
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Moneda",
    )
    partner_city = fields.Char(
        string="Municipio",
        related="partner_id.city",
        readonly=True,
        store=True,
    )

    @api.depends('sale_order_ids.amount_total')
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(order.sale_order_ids.mapped('amount_total'))

    @api.depends('equipment_line_ids')
    def _compute_equipment_count(self):
        """Contar el número de equipos en las líneas."""
        for order in self:
            order.equipment_count = len(order.equipment_line_ids)

    @api.onchange('partner_id')
    def _onchange_partner_id_equipment_ids(self):
        if self.partner_id:
            # Limpiar equipos que no correspondan al cliente seleccionado
            equipos_validos = self.equipment_ids.filtered(lambda eq: eq.customer_id == self.partner_id)
            self.equipment_ids = equipos_validos
            # También limpiar líneas de equipos no válidas
            lineas_validas = self.equipment_line_ids.filtered(lambda l: l.equipment_id.customer_id == self.partner_id)
            if len(lineas_validas) != len(self.equipment_line_ids):
                self.equipment_line_ids = [(6, 0, lineas_validas.ids)]
            
            domain = [('customer_id', '=', self.partner_id.id)]
            return {'domain': {'equipment_ids': domain}}
        self.equipment_ids = False
        self.equipment_line_ids = False
        return {'domain': {'equipment_ids': []}}

    @api.onchange('equipment_ids')
    def _onchange_equipment_ids(self):
        """Sincronizar Many2many equipment_ids con One2many equipment_line_ids"""
        if self.equipment_ids:
            # Equipos actualmente en las líneas
            existing_equip_ids = self.equipment_line_ids.mapped('equipment_id.id')
            selected_equip_ids = self.equipment_ids.ids
            
            # Líneas a eliminar (están en lines pero no en el Many2many seleccionado)
            lines_to_remove = self.equipment_line_ids.filtered(lambda l: l.equipment_id.id not in selected_equip_ids)
            for line in lines_to_remove:
                self.equipment_line_ids = [(2, line.id, 0)]
                
            # Líneas a añadir (están en Many2many pero no en las líneas)
            for equip_id in selected_equip_ids:
                if equip_id not in existing_equip_ids:
                    equipment = self.env['maintenance.equipment'].browse(equip_id)
                    self.equipment_line_ids = [(0, 0, {
                        'equipment_id': equip_id,
                        'survey_id': equipment.default_survey_id.id if equipment.default_survey_id else False,
                    })]

    @api.onchange('equipment_line_ids')
    def _onchange_equipment_line_ids(self):
        """Sincronizar One2many equipment_line_ids con Many2many equipment_ids"""
        if self.equipment_line_ids:
            equipment_ids = self.equipment_line_ids.mapped('equipment_id')
            self.equipment_ids = [(6, 0, equipment_ids.ids)]
        else:
            self.equipment_ids = [(5, 0, 0)]


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

        # Obtener el tipo de venta 'Reparación'
        type_id = self.env.ref('palmalube_sale_type.sale_order_type_reparacion', raise_if_not_found=False)

        sale_order_vals = {
            'partner_id': self.partner_id.id,
            'fsm_order_id': self.id,  # Relaciona la orden de venta con el fsm.order
            'type_id': type_id.id if type_id else False,
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


