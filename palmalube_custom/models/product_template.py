# Copyright 2025 Ivan Parrado, Manuel Calero, Abraham Carrasco, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.tools.translate import _

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def write(self, vals):
        """
        Override del método write para permitir cambiar is_storable a True
        incluso cuando ya existen movimientos de stock realizados.

        Esto elimina la restricción de Odoo 18 que impide cambiar el tipo de producto
        cuando ya se han realizado ventas o movimientos de stock.
        """
        # Si se está intentando cambiar is_storable, removemos todas las validaciones de stock
        if 'is_storable' in vals:
            # Solo mantenemos validaciones críticas al cambiar a NO almacenable

            # Validación de reordering rules (solo al cambiar a no-storable)
            if not vals['is_storable'] and sum(self.mapped('nbr_reordering_rules')) != 0:
                raise UserError(_('You still have some active reordering rules on this product. Please archive or delete them first.'))

            # Validación de cantidad disponible (solo al cambiar a no-storable)
            if not vals['is_storable'] and any(p.is_storable and not float_is_zero(p.qty_available, precision_rounding=p.uom_id.rounding) for p in self):
                raise UserError(_("Available quantity should be set to zero before changing inventory tracking"))

            # REMOVEMOS TODAS LAS VALIDACIONES DE MOVIMIENTOS (done y reserved)
            # Permitimos cambiar is_storable sin restricciones de stock
            # Saltamos el write de stock.models.ProductTemplate completamente
            return models.Model.write(self, vals)

        # Si no se está cambiando is_storable, comportamiento normal
        return super().write(vals)
