# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    fsm_order_equipment_line_id = fields.Many2one(
        "fsm.order.equipment.line",
        string="Línea de Equipo FSM",
        ondelete="cascade",
        help="Línea de equipo vinculada a esta respuesta de encuesta",
    )
    fsm_order_id = fields.Many2one(
        "fsm.order",
        string="Orden FSM",
        ondelete="cascade",
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Pedido de Venta",
        help="Pedido de venta relacionado con esta encuesta",
        copy=False,
    )
    has_sale_order = fields.Boolean(
        string="Tiene Pedido",
        compute="_compute_has_sale_order",
        store=True,
    )
    next_maintenance_date = fields.Date(
        string="Próxima Revisión",
        related="fsm_order_id.next_maintenance_date",
        readonly=True,
        store=True,
        help="Fecha de la próxima revisión/mantenimiento",
    )
    fsm_order_amount_total = fields.Monetary(
        string="Precio",
        related="fsm_order_id.amount_total",
        readonly=True,
        store=True,
        currency_field="fsm_order_currency_id",
        help="Importe total de la orden FSM",
    )
    fsm_order_currency_id = fields.Many2one(
        "res.currency",
        related="fsm_order_id.company_currency_id",
        readonly=True,
        store=True,
    )

    @api.depends('sale_order_id', 'fsm_order_id.sale_order_ids')
    def _compute_has_sale_order(self):
        """Verifica si existe un pedido de venta asociado directamente o a través del FSM Order."""
        for record in self:
            # Tiene pedido si está vinculado directamente O si el FSM Order tiene pedidos
            record.has_sale_order = bool(record.sale_order_id) or bool(record.fsm_order_id.sale_order_ids)

    def write(self, vals):
        """Forzar recomputación de survey_state cuando cambia el estado de la encuesta."""
        result = super().write(vals)
        if 'state' in vals:
            # Obtener las líneas de equipo vinculadas
            lines = self.filtered(lambda r: r.fsm_order_equipment_line_id).mapped('fsm_order_equipment_line_id')
            if lines:
                # Forzar recomputación del campo survey_state
                lines._compute_survey_state()
                # Publicar mensaje si se completó
                if vals['state'] == 'done':
                    for line in lines:
                        line.fsm_order_id.message_post(
                            body=_("Encuesta completada para el equipo: %s") % line.equipment_id.name,
                            message_type="notification",
                        )
        return result

    def action_create_sale_order(self):
        """Crea un pedido de venta desde la encuesta."""
        self.ensure_one()

        # Validar que tenga FSM order
        if not self.fsm_order_id:
            raise models.ValidationError(_("Esta encuesta no está vinculada a ninguna orden FSM."))

        # Obtener el tipo de venta 'Reparación'
        type_id = self.env.ref('palmalube_sale_type.sale_order_type_reparacion', raise_if_not_found=False)

        # Si ya tiene pedido directo, crear uno nuevo solo en FSM
        if self.sale_order_id:
            # Crear pedido adicional vinculado solo al FSM
            sale_order = self.env['sale.order'].create({
                'partner_id': self.fsm_order_id.partner_id.id,
                'fsm_order_id': self.fsm_order_id.id,
                'type_id': type_id.id if type_id else False,
                'origin': _('Encuesta: %s - FSM: %s') % (self.survey_id.title, self.fsm_order_id.name),
            })
        else:
            # Crear el pedido de venta vinculado a encuesta Y fsm
            sale_order = self.env['sale.order'].create({
                'partner_id': self.fsm_order_id.partner_id.id,
                'fsm_order_id': self.fsm_order_id.id,
                'type_id': type_id.id if type_id else False,
                'origin': _('Encuesta: %s - FSM: %s') % (self.survey_id.title, self.fsm_order_id.name),
            })

            # Vincular el pedido a la encuesta (solo si no tenía)
            self.sale_order_id = sale_order.id

        # Retornar acción para abrir el pedido
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedido de Venta'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_sale_order(self):
        """Abre TODOS los pedidos relacionados (directo de survey + pedidos del FSM)."""
        self.ensure_one()

        # Recopilar TODOS los pedidos relacionados
        sale_order_ids = []

        # 1. Pedido directo de la encuesta
        if self.sale_order_id:
            sale_order_ids.append(self.sale_order_id.id)

        # 2. Pedidos del FSM Order (que NO estén ya incluidos)
        if self.fsm_order_id and self.fsm_order_id.sale_order_ids:
            for order in self.fsm_order_id.sale_order_ids:
                if order.id not in sale_order_ids:
                    sale_order_ids.append(order.id)

        # Si no hay pedidos, mostrar error
        if not sale_order_ids:
            raise models.ValidationError(_("Esta encuesta no tiene ningún pedido de venta asociado."))

        # Si solo hay un pedido total, abrirlo directamente
        if len(sale_order_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Pedido de Venta'),
                'res_model': 'sale.order',
                'res_id': sale_order_ids[0],
                'view_mode': 'form',
                'target': 'current',
            }

        # Si hay múltiples pedidos, mostrar lista con TODOS
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedidos de Venta'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', sale_order_ids)],
            'target': 'current',
        }


