from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_limited_contacts_group(self):
        return self.env.ref('palmalube_limited_contact_by_salesperson.group_palmalube_limited_contacts_salesperson')

    @api.model
    def _get_contact_domain(self):
        user = self.env.user
        limited_group = self._get_limited_contacts_group()
        if limited_group in user.groups_id:
            return [('user_id', '=', user.id)]
        return []

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        contact_domain = self._get_contact_domain()
        if contact_domain:
            if args and len(args) > 0:
                args = ['&'] + contact_domain + args
            else:
                args = contact_domain
        if count:
            return self.search_count(args)
        return super(ResPartner, self).search(args, offset=offset, limit=limit, order=order)

    @api.model
    def search_count(self, args, *other_args, **other_kwargs):
        contact_domain = self._get_contact_domain()
        if contact_domain:
            if args and len(args) > 0:
                args = ['&'] + contact_domain + args
            else:
                args = contact_domain
        return super(ResPartner, self).search_count(args, *other_args, **other_kwargs)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        contact_domain = self._get_contact_domain()
        if contact_domain:
            if domain and len(domain) > 0:
                domain = ['&'] + contact_domain + domain
            else:
                domain = contact_domain
        return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def read(self, fields=None, load='_classic_read'):
        contact_domain = self._get_contact_domain()
        if contact_domain:
            filtered = self.filtered(lambda r: r.user_id and r.user_id.id == self.env.user.id)
            return super(ResPartner, filtered).read(fields=fields, load=load)
        return super(ResPartner, self).read(fields=fields, load=load)
