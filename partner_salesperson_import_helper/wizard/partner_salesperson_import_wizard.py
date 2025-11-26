from odoo import models, fields, _
from odoo.exceptions import UserError
import base64
import io
import pandas as pd
import logging

_logger = logging.getLogger(__name__)

class PartnerSalespersonImportWizard(models.TransientModel):
    _name = 'partner.salesperson.import.wizard'
    _description = 'Importador de comerciales para clientes'

    file = fields.Binary('Archivo Excel', required=True)
    filename = fields.Char('Nombre del archivo')

    def action_import(self):
        if not self.file:
            raise UserError(_('Por favor, suba un archivo.'))
        try:
            data = base64.b64decode(self.file)
            df = pd.read_excel(io.BytesIO(data))
            # Normalizar nombres de columnas para evitar errores por espacios, mayúsculas o guiones
            df.columns = [c.strip().lower().replace(' ', '_').replace('-', '_') for c in df.columns]
        except Exception as e:
            raise UserError(_('Error leyendo el archivo: %s') % e)
        # Mapear nombres de columnas originales en mayúsculas a los nombres internos
        col_map = {
            'id_cliente': 'id_cliente',
            'nombreagente': 'nombreagente',
            'apellidosagente': 'apellidosagente',
            'razon_social': 'razon_social',
            'direccion': 'direccion',
            'cif': 'cif',
            'telefono_fijo': 'telefono_fijo',
            'telefono_movil': 'telefono_movil',
            'email': 'email',
        }
        for col in col_map:
            if col not in df.columns:
                # Intentar buscar la columna en mayúsculas
                col_upper = col.upper()
                if col_upper in [c.upper() for c in df.columns]:
                    idx = [c.upper() for c in df.columns].index(col_upper)
                    df.rename(columns={df.columns[idx]: col}, inplace=True)
                else:
                    raise UserError(_('El archivo debe tener la columna: %s') % col)
        updated = 0
        not_found = []
        not_updated = []
        # Llevar control de los clientes ya procesados para evitar duplicados
        clientes_procesados = set()
        # Definir variables de columna para uso posterior
        col_cliente = 'id_cliente'
        col_nombre = 'nombreagente'
        col_apellidos = 'apellidosagente'
        col_razon = 'razon_social'
        col_direccion = 'direccion'
        col_cif = 'cif'
        col_telefono = 'telefono_fijo'
        col_movil = 'telefono_movil'
        col_email = 'email'
        col_cp = 'codigopostal'
        col_ciudad = 'muni_descr'
        col_provincia = 'provi_descr'
        # Añadir las nuevas columnas a la comprobación
        for col in [col_cp, col_ciudad, col_provincia]:
            if col not in df.columns:
                col_upper = col.upper()
                if col_upper in [c.upper() for c in df.columns]:
                    idx = [c.upper() for c in df.columns].index(col_upper)
                    df.rename(columns={df.columns[idx]: col}, inplace=True)
                else:
                    raise UserError(_('El archivo debe tener la columna: %s') % col)
        for idx, row in df.iterrows():
            try:
                # Usar el valor original de la celda, sin convertir a int, para evitar perder ceros
                raw_cliente = row[col_cliente]
                if pd.isnull(raw_cliente):
                    codigo_cliente = None
                else:
                    codigo_cliente = str(raw_cliente).strip()
                nombre_agente = str(row[col_nombre]).strip() if pd.notnull(row[col_nombre]) else ''
                apellidos_agente = str(row[col_apellidos]).strip() if pd.notnull(row[col_apellidos]) else ''
                nombre_completo = f"{nombre_agente} {apellidos_agente}".strip()
                nombre_completo_lower = nombre_completo.lower()
                cp = str(row[col_cp]).strip() if pd.notnull(row[col_cp]) else ''
                ciudad = str(row[col_ciudad]).strip() if pd.notnull(row[col_ciudad]) else ''
                provincia = str(row[col_provincia]).strip() if pd.notnull(row[col_provincia]) else ''
            except Exception:
                not_found.append((row.get(col_cliente), '', 'Datos no válidos'))
                continue
            if not codigo_cliente or not nombre_completo:
                not_found.append((row.get(col_cliente), '', 'Datos vacíos'))
                continue
            # Evitar procesar el mismo cliente más de una vez
            if codigo_cliente in clientes_procesados:
                continue
            clientes_procesados.add(codigo_cliente)
            _logger.info(f"Buscando partner con ref={codigo_cliente}")
            partner = self.env['res.partner'].sudo().search([('ref', '=', codigo_cliente)], limit=1)
            # Si no encuentra, intentar con ceros a la derecha hasta 4 dígitos
            if not partner and codigo_cliente.isdigit() and len(codigo_cliente) < 4:
                for extra_zeros in range(1, 5 - len(codigo_cliente)):
                    ref_ceros = codigo_cliente + ('0' * extra_zeros)
                    _logger.info(f"Intentando buscar partner con ref={ref_ceros}")
                    partner = self.env['res.partner'].sudo().search([('ref', '=', ref_ceros)], limit=1)
                    if partner:
                        break
            # Si sigue sin encontrar, crearlo con los datos del Excel
            if not partner:
                # Buscar por nombre y/o email antes de crear para evitar duplicados (sin exigir NIF válido)
                search_domain = [('name', '=', str(row[col_razon]).strip())]
                email_excel = str(row[col_email]).strip() if pd.notnull(row[col_email]) else ''
                if email_excel:
                    search_domain.append(('email', '=', email_excel))
                partner = self.env['res.partner'].sudo().search(search_domain, limit=1)
            if not partner:
                try:
                    vals_partner = {
                        'ref': codigo_cliente,
                        'name': str(row[col_razon]).strip() if pd.notnull(row[col_razon]) else '',
                        'street': str(row[col_direccion]).strip() if pd.notnull(row[col_direccion]) else '',
                        'zip': cp,
                        'city': ciudad,
                        'state_id': False,  # Se buscará la provincia abajo
                        'vat': str(row[col_cif]) if pd.notnull(row[col_cif]) else '',  # Insertar NIF tal cual, sin strip ni validación
                        'phone': str(row[col_telefono]).strip() if pd.notnull(row[col_telefono]) else '',
                        'mobile': str(row[col_movil]).strip() if pd.notnull(row[col_movil]) else '',
                        'email': email_excel,
                        'country_id': self.env.ref('base.es').id if self.env.ref('base.es', raise_if_not_found=False) else False,
                        'company_type': 'company',
                        'is_company': True,
                        'customer_rank': 1,
                    }
                    # Buscar provincia (state_id) por nombre
                    state = self.env['res.country.state'].sudo().search([
                        ('name', 'ilike', provincia),
                        ('country_id', '=', vals_partner['country_id'])
                    ], limit=1) if provincia and vals_partner['country_id'] else False
                    if state:
                        vals_partner['state_id'] = state.id
                    partner = self.env['res.partner'].sudo().create(vals_partner)
                    _logger.info(f"Partner creado: {partner.id} {partner.name}")
                except Exception as e:
                    not_found.append((codigo_cliente, '', f"No se pudo crear partner: {e}"))
                    _logger.error(f"No se pudo crear partner {codigo_cliente}: {e}")
                    continue
            # Buscar usuario comercial por nombre completo normalizado o login generado
            login = f"auto_user_{nombre_completo_lower.replace(' ', '_')}@import.local"
            user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
            if not user:
                # Buscar por nombre normalizado (ignorando mayúsculas, tildes y espacios)
                def normalize(s):
                    import unicodedata
                    return ''.join(c for c in unicodedata.normalize('NFKD', s.lower()) if not unicodedata.combining(c)).replace(' ', '')
                nombre_normalizado = normalize(nombre_completo)
                users = self.env['res.users'].sudo().search([])
                for u in users:
                    if u.name and normalize(u.name) == nombre_normalizado:
                        user = u
                        _logger.info(f"Usuario comercial ya existía por nombre normalizado: {user.id} ({user.name})")
                        break
            if not user:
                # Crear usuario con nombre completo y login único
                # Formatear nombre completo: primera letra de cada palabra en mayúscula, resto en minúscula
                def titlecase(s):
                    return ' '.join([w.capitalize() for w in s.split()])
                nombre_completo_title = titlecase(nombre_completo)
                vals = {
                    'login': login,
                    'name': nombre_completo_title,
                }
                try:
                    user = self.env['res.users'].sudo().create(vals)
                    _logger.info(f"Usuario comercial creado: {user.id} ({user.name})")
                except Exception as e:
                    not_found.append((codigo_cliente, nombre_completo, f"No se pudo crear usuario: {e}"))
                    _logger.error(f"No se pudo crear usuario {nombre_completo}: {e}")
                    continue
            # Asignar el comercial encontrado o creado al cliente
            try:
                partner.sudo().write({'user_id': user.id})
                partner = self.env['res.partner'].sudo().browse(partner.id)
                _logger.info(f"user_id después={partner.user_id.id}")
                if partner.user_id.id == user.id:
                    updated += 1
                    _logger.info(f"Asignado user_id {user.id} a partner {partner.id}")
                else:
                    not_updated.append((codigo_cliente, nombre_completo, f"No se pudo actualizar (user_id previo: {partner.user_id.id})"))
                    _logger.warning(f"No se pudo actualizar user_id para partner {partner.id}")
            except Exception as e:
                not_updated.append((codigo_cliente, nombre_completo, f"Error: {e}"))
                _logger.error(f"Error actualizando partner {partner.id}: {e}")
        msg = _('Clientes actualizados: %s') % updated
        if not_found:
            msg += _('\nNo encontrados o inválidos: %s') % ', '.join([f"{c}/{u} ({r})" for c,u,r in not_found])
        if not_updated:
            msg += _('\nNo actualizados: %s') % ', '.join([f"{c}/{u} ({r})" for c,u,r in not_updated])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'partner.salesperson.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': _('Resultado de la importación'),
            'context': dict(self.env.context, default_filename=self.filename),
            'views': [(False, 'form')],
            'flags': {'form': {'action_buttons': False}},
            'message': msg,
        }
