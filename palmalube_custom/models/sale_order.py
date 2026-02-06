# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        """Cancelar pedido de venta directamente sin wizard"""
        return self.write({"state": "cancel"})

    def _get_order_lines_to_report(self):
        lines = super()._get_order_lines_to_report()
        # Filtra para asegurar que todos los elementos sean instancias válidas de sale.order.line
        lines = lines.filtered(lambda l: l and l._name == 'sale.order.line')
        return lines

    tiene_equipos_o_intervencion = fields.Boolean(
        string="¿Tiene equipos o intervención?",
        compute="_compute_tiene_equipos_o_intervencion",
        store=True,
    )

    def _compute_tiene_equipos_o_intervencion(self):
        for order in self:
            order.tiene_equipos_o_intervencion = any(
                bool(getattr(line, 'equipo_ids', False)) or bool(getattr(line, 'intervencion', False))
                for line in order.order_line
            )

    # Campo computado para contar FSM Orders relacionadas
    # Nota: fsm_order_id ya está definido en xtendoo_fsm
    # Nota: survey_count y survey_user_input_ids ya están definidos en palmalube_fsm_order
    # Nota: Los métodos action_view_surveys y action_view_fsm_order ya están en palmalube_fsm_order

