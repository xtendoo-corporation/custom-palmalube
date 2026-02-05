# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    survey_user_input_ids = fields.One2many(
        "survey.user_input",
        "sale_order_id",
        string="Encuestas Directas",
        help="Encuestas vinculadas directamente a este pedido"
    )
    survey_count = fields.Integer(
        string="Número de Encuestas",
        compute="_compute_survey_count",
    )

    @api.depends('survey_user_input_ids', 'fsm_order_id.equipment_line_ids.survey_user_input_id')
    def _compute_survey_count(self):
        """Contar TODAS las encuestas relacionadas (directas + del FSM Order)."""
        for order in self:
            survey_ids = set()

            # 1. Encuestas directas del sale_order
            if order.survey_user_input_ids:
                survey_ids.update(order.survey_user_input_ids.ids)

            # 2. Encuestas del FSM Order relacionado
            if order.fsm_order_id and order.fsm_order_id.equipment_line_ids:
                for line in order.fsm_order_id.equipment_line_ids:
                    if line.survey_user_input_id:
                        survey_ids.add(line.survey_user_input_id.id)

            order.survey_count = len(survey_ids)

    def action_view_surveys(self):
        """Abre TODAS las encuestas relacionadas (directas + del FSM Order)."""
        self.ensure_one()

        # Recopilar TODAS las encuestas relacionadas
        survey_ids = set()

        # 1. Encuestas directas
        if self.survey_user_input_ids:
            survey_ids.update(self.survey_user_input_ids.ids)

        # 2. Encuestas del FSM Order
        if self.fsm_order_id and self.fsm_order_id.equipment_line_ids:
            for line in self.fsm_order_id.equipment_line_ids:
                if line.survey_user_input_id:
                    survey_ids.add(line.survey_user_input_id.id)

        if not survey_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin Encuestas'),
                    'message': _('Este pedido no tiene encuestas relacionadas.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        survey_list = list(survey_ids)

        # Si solo hay una encuesta, abrir en modo formulario
        if len(survey_list) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Encuesta'),
                'res_model': 'survey.user_input',
                'view_mode': 'form',
                'res_id': survey_list[0],
                'target': 'current',
            }

        # Si hay múltiples encuestas, mostrar en vista lista
        return {
            'type': 'ir.actions.act_window',
            'name': _('Encuestas'),
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', survey_list)],
            'target': 'current',
        }

    def action_view_fsm_order(self):
        """Abre la orden FSM relacionada."""
        self.ensure_one()

        if not self.fsm_order_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin Orden FSM'),
                    'message': _('Este pedido no tiene una orden FSM relacionada.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden FSM'),
            'res_model': 'fsm.order',
            'view_mode': 'form',
            'res_id': self.fsm_order_id.id,
            'target': 'current',
        }
