from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    comercial_id = fields.Many2one(
        comodel_name='res.users',
        string='Comercial',
        readonly=True,
        copy=False,
        default=lambda self: self.env.user,
    )

    @api.model
    def create(self, vals):
        if not vals.get('comercial_id'):
            vals['comercial_id'] = self.env.uid
        return super().create(vals)

    @api.model
    def _update_comercial_id_from_chatter(self):
        # Solo para pagos antiguos sin comercial_id
        payments = self.search([('comercial_id', '!=', False)])
        print(f"Pagos a actualizar: {len(payments)}")
        Message = self.env['mail.message']
        for payment in payments:
            print(f"Procesando pago ID: {payment.id}")
            # Buscar el primer mensaje de creación relacionado con este pago
            msg = Message.search([
                ('model', '=', 'account.payment'),
                ('res_id', '=', payment.id),
                ('message_type', '=', 'notification'),
                ('subtype_id', '=', self.env.ref('mail.mt_note').id),
            ], order='date asc', limit=1)
            if not msg:
                print(f"No se encontró mensaje tipo 'note' para pago {payment.id}, buscando 'comment'")
                # Buscar cualquier mensaje de tipo 'comment' si no hay 'note'
                msg = Message.search([
                    ('model', '=', 'account.payment'),
                    ('res_id', '=', payment.id),
                    ('message_type', '=', 'comment'),
                ], order='date asc', limit=1)
            if msg:
                print(f"Mensaje encontrado para pago {payment.id}: autor_id={msg.author_id.id if msg.author_id else None}")
            else:
                print(f"No se encontró ningún mensaje para pago {payment.id}")
            if msg and msg.author_id:
                user = self.env['res.users'].search([('partner_id', '=', msg.author_id.id)], limit=1)
                if user:
                    print(f"Asignando comercial_id={user.id} a pago {payment.id}")
                    payment.comercial_id = user.id
                else:
                    print(f"No se encontró usuario para partner_id={msg.author_id.id} en pago {payment.id}")
            else:
                print(f"No se puede asignar comercial para pago {payment.id}")
