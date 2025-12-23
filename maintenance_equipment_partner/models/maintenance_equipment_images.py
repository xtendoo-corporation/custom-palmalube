from odoo import fields, models


class MaintenanceEquipmentImage(models.Model):
    _name = 'maintenance.equipment.image'
    _description = 'Imagen adicional de equipo de mantenimiento'

    equipment_id = fields.Many2one(
        comodel_name='maintenance.equipment',
        string='Equipo',
        required=True,
        ondelete='cascade',
    )
    image = fields.Image(
        string='Imagen',
        max_width=1920,
        max_height=1920,
        required=True,
    )
    name = fields.Char(string='Descripción')
