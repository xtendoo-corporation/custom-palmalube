# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    tiene_equipos_o_intervencion = fields.Boolean(
        string="¿Tiene equipos o intervención?",
        compute="_compute_tiene_equipos_o_intervencion",
        store=True,
    )

    def _compute_tiene_equipos_o_intervencion(self):
        for move in self:
            move.tiene_equipos_o_intervencion = any(
                bool(getattr(line, 'equipo_ids', False)) or bool(getattr(line, 'intervencion', False))
                for line in move.invoice_line_ids
            )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Sobrescribir _search para aplicar restricciones de seguridad.

        Si el usuario pertenece al grupo 'group_palmalube_limited_contacts_salesperson'
        y NO es manager, solo verá facturas donde él es el invoice_user_id.
        """
        # Obtener el usuario actual
        user = self.env.user

        # Verificar si el usuario tiene el grupo de comerciales limitados
        try:
            limited_group = self.env.ref(
                'palmalube_limited_contact_by_salesperson.group_palmalube_limited_contacts_salesperson',
                raise_if_not_found=False
            )
        except:
            limited_group = None

        # Si el usuario tiene el grupo limitado
        if limited_group and limited_group in user.groups_id:
            # Verificar si NO es manager
            try:
                manager_group = self.env.ref('account.group_account_manager', raise_if_not_found=False)
            except:
                manager_group = None

            # Si NO es manager, aplicar restricción
            if not manager_group or manager_group not in user.groups_id:
                # Agregar restricción: solo facturas donde el usuario es el vendedor
                domain = domain + [('invoice_user_id', '=', user.id)]

        return super()._search(domain, offset=offset, limit=limit, order=order)
