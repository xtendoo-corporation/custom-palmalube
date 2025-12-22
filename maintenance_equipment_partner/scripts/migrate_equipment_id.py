# Script de migración para convertir equipment_id de Many2one a Many2many en repair.order
# Ejecutar en entorno Odoo shell tras actualizar el módulo

from odoo import api, SUPERUSER_ID

def migrate_equipment_id_to_many2many(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    repairs = env['repair.order'].search([])
    for repair in repairs:
        if repair.equipment_id:
            repair.write({'equipment_ids': [(4, repair.equipment_id.id)]})

# Guardar este archivo como scripts/migrate_equipment_id.py y ejecutarlo tras la migración del módulo.
