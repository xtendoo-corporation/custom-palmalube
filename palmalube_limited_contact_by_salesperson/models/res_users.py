from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    limited_contacts_salesperson = fields.Boolean(
        string='Filtrado por Comercial',
        help='Si está marcado, el usuario sólo verá los contactos asignados como comercial.',
    )

    @api.model
    def _get_limited_contacts_group(self):
        return self.env.ref('palmalube_limited_contact_by_salesperson.group_palmalube_limited_contacts_salesperson')

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        group = self._get_limited_contacts_group()
        for user in self:
            if 'limited_contacts_salesperson' in vals:
                if vals['limited_contacts_salesperson']:
                    if group not in user.groups_id:
                        user.groups_id = [(4, group.id)]
                else:
                    if group in user.groups_id:
                        user.groups_id = [(3, group.id)]
        return res

    @api.model
    def create(self, vals):
        user = super(ResUsers, self).create(vals)
        group = self._get_limited_contacts_group()
        if vals.get('limited_contacts_salesperson'):
            if group not in user.groups_id:
                user.groups_id = [(4, group.id)]
        return user

