from odoo import models

class ResPartner(models.Model):
    """
    Este modelo se mantiene para futuras extensiones.
    La restricción de visibilidad se maneja completamente mediante
    reglas de registro (ir.rule) en security/limited_contacts_security.xml
    """
    _inherit = 'res.partner'

