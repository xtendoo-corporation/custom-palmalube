# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import csv
import io
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class ImportInvoiceWizard(models.TransientModel):
    _name = "import.invoice.wizard"
    _description = "Importar Facturas desde CSV (Palmalube)"

    csv_file = fields.Binary(
        string="Archivo CSV",
        required=True,
        help="Archivo CSV con facturas. Formato: move_type,name,invoice_date,"
        "partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id",
    )
    csv_filename = fields.Char(string="Nombre del archivo")

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario",
        required=True,
        domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]",
    )
    expense_account_id = fields.Many2one(
        "account.account",
        string="Cuenta de Gasto (Base)",
        required=True,
        domain="[('account_type', 'in', ['expense', 'expense_depreciation', "
        "'expense_direct_cost']), ('company_id', '=', company_id)]",
        help="Cuenta contable para la base imponible",
    )
    tax_account_id = fields.Many2one(
        "account.account",
        string="Cuenta de IVA Soportado",
        required=True,
        domain="[('company_id', '=', company_id)]",
        help="Cuenta contable para el IVA soportado",
    )
    payable_account_id = fields.Many2one(
        "account.account",
        string="Cuenta a Pagar (Opcional)",
        domain="[('account_type', '=', 'liability_payable'), "
        "('company_id', '=', company_id)]",
        help="Dejar en blanco para usar la cuenta del proveedor",
    )

    create_partners = fields.Boolean(
        string="Crear proveedores si no existen",
        default=True,
        help="Si está marcado, crea automáticamente proveedores nuevos",
    )
    dry_run = fields.Boolean(
        string="Modo simulación (dry-run)",
        default=False,
        help="Solo valida el CSV sin crear facturas",
    )

    # Resultados
    result_message = fields.Html(string="Resultado", readonly=True)
    total_rows = fields.Integer(string="Filas procesadas", readonly=True)
    created_count = fields.Integer(string="Facturas creadas", readonly=True)
    skipped_count = fields.Integer(string="Duplicados saltados", readonly=True)
    error_count = fields.Integer(string="Errores", readonly=True)
    error_log = fields.Text(string="Log de errores", readonly=True)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        """Resetear campos relacionados con la compañía."""
        self.journal_id = False
        self.expense_account_id = False
        self.tax_account_id = False
        self.payable_account_id = False

    def _parse_csv_line_robust(self, row_string, line_number):
        """
        Parser robusto para CSV con partner_name que puede contener comas.

        Estrategia:
        - Los 3 primeros campos son fijos: move_type, name, invoice_date
        - Los 5 últimos campos son fijos: amount_untaxed, amount_tax,
          amount_total, state, currency_id
        - Todo lo que quede en medio es partner_name

        Args:
            row_string: string crudo de la línea CSV
            line_number: número de línea para logging

        Returns:
            dict con los campos parseados o None si hay error
        """
        try:
            # Intentar primero con csv.reader estándar
            reader = csv.reader([row_string])
            fields_list = next(reader)

            # Si tenemos exactamente 9 campos, es directo
            if len(fields_list) == 9:
                return {
                    'move_type': fields_list[0].strip(),
                    'name': fields_list[1].strip(),
                    'invoice_date': fields_list[2].strip(),
                    'partner_name': fields_list[3].strip().strip('"'),
                    'amount_untaxed': fields_list[4].strip(),
                    'amount_tax': fields_list[5].strip(),
                    'amount_total': fields_list[6].strip(),
                    'state': fields_list[7].strip(),
                    'currency_id': fields_list[8].strip(),
                }

            # Si tenemos más de 9 campos, el partner tiene comas
            if len(fields_list) > 9:
                # Los primeros 3
                move_type = fields_list[0].strip()
                name = fields_list[1].strip()
                invoice_date = fields_list[2].strip()

                # Los últimos 5
                currency_id = fields_list[-1].strip()
                state = fields_list[-2].strip()
                amount_total = fields_list[-3].strip()
                amount_tax = fields_list[-4].strip()
                amount_untaxed = fields_list[-5].strip()

                # Todo lo del medio es el partner
                partner_parts = fields_list[3:-5]
                partner_name = ",".join(partner_parts).strip().strip('"')

                return {
                    'move_type': move_type,
                    'name': name,
                    'invoice_date': invoice_date,
                    'partner_name': partner_name,
                    'amount_untaxed': amount_untaxed,
                    'amount_tax': amount_tax,
                    'amount_total': amount_total,
                    'state': state,
                    'currency_id': currency_id,
                }

            # Si tenemos menos de 9 campos, error
            raise ValueError(f"Línea {line_number}: esperados 9+ campos, encontrados {len(fields_list)}")

        except Exception as e:
            _logger.error(f"Error parseando línea {line_number}: {e}")
            return None

    def _validate_and_convert_amounts(self, row_data, line_number, currency):
        """
        Valida y convierte los importes a Decimal con precisión de la moneda.

        Args:
            row_data: dict con los datos parseados
            line_number: número de línea
            currency: res.currency record

        Returns:
            tuple (untaxed_decimal, tax_decimal, total_decimal) o None si error
        """
        try:
            untaxed = Decimal(row_data['amount_untaxed'])
            tax = Decimal(row_data['amount_tax'])
            total = Decimal(row_data['amount_total'])

            # Redondear según la moneda
            precision = currency.decimal_places
            untaxed = untaxed.quantize(
                Decimal(10) ** -precision, rounding=ROUND_HALF_UP
            )
            tax = tax.quantize(
                Decimal(10) ** -precision, rounding=ROUND_HALF_UP
            )
            total = total.quantize(
                Decimal(10) ** -precision, rounding=ROUND_HALF_UP
            )

            # Validar que base + IVA = total (con tolerancia)
            calculated_total = untaxed + tax
            diff = abs(calculated_total - total)
            tolerance = Decimal("0.02")  # 2 céntimos de tolerancia

            if diff > tolerance:
                raise ValueError(
                    f"Base ({untaxed}) + IVA ({tax}) = {calculated_total} "
                    f"no coincide con total ({total}). Diferencia: {diff}"
                )

            return float(untaxed), float(tax), float(total)

        except (ValueError, TypeError) as e:
            _logger.error(
                f"Línea {line_number}: error convirtiendo importes: {e}"
            )
            return None

    def _get_or_create_partner(self, partner_name):
        """
        Busca o crea un proveedor por nombre.

        Args:
            partner_name: nombre del proveedor

        Returns:
            res.partner record
        """
        # Normalizar nombre (quitar espacios extras, case-insensitive)
        normalized_name = " ".join(partner_name.split()).strip()

        partner = self.env["res.partner"].search(
            [
                ("name", "=ilike", normalized_name),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

        if partner:
            # Asegurar que es proveedor
            if partner.supplier_rank == 0:
                partner.supplier_rank = 1
            return partner

        # Crear nuevo si está permitido
        if not self.create_partners:
            raise UserError(
                _("Proveedor '%s' no existe y la opción de crear "
                  "proveedores está desactivada") % partner_name
            )

        partner = self.env["res.partner"].create({
            "name": normalized_name,
            "supplier_rank": 1,
            "company_id": self.company_id.id,
        })
        _logger.info(f"Proveedor creado: {partner.name} (ID: {partner.id})")
        return partner

    def _check_duplicate(self, ref, partner_id, invoice_date, move_type):
        """
        Verifica si ya existe una factura con los mismos datos.

        Args:
            ref: referencia de proveedor
            partner_id: ID del proveedor
            invoice_date: fecha de factura
            move_type: tipo de movimiento

        Returns:
            bool: True si existe duplicado
        """
        existing = self.env["account.move"].search(
            [
                ("ref", "=", ref),
                ("partner_id", "=", partner_id),
                ("invoice_date", "=", invoice_date),
                ("move_type", "=", move_type),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        return bool(existing)

    def _create_invoice_lines(
        self, move, untaxed, tax, total, currency, payable_account
    ):
        """
        Crea las líneas contables (line_ids) para cuadrar exactamente.

        Estrategia:
        - Línea 1: Gasto/compra por base (debit=untaxed si positivo)
        - Línea 2: IVA soportado por tax (debit=tax si positivo)
        - Línea 3: A pagar proveedor por total (credit=total si positivo)

        Para refund (negativos), invertir signos.

        Args:
            move: account.move record
            untaxed: importe base (float)
            tax: importe IVA (float)
            total: importe total (float)
            currency: res.currency record
            payable_account: account.account para proveedor
        """
        is_refund = move.move_type == "in_refund"

        # Determinar signos
        # En in_invoice: debit para gastos/IVA, credit para proveedor
        # En in_refund: credit para gastos/IVA, debit para proveedor

        line_vals = []

        # Línea 1: Base imponible (gasto)
        if not float_is_zero(untaxed, precision_rounding=currency.rounding):
            debit_untaxed = abs(untaxed) if not is_refund else 0.0
            credit_untaxed = 0.0 if not is_refund else abs(untaxed)

            line_vals.append((0, 0, {
                "account_id": self.expense_account_id.id,
                "name": move.ref or "Base imponible",
                "debit": debit_untaxed,
                "credit": credit_untaxed,
                "partner_id": move.partner_id.id,
                "currency_id": currency.id,
                "exclude_from_invoice_tab": False,
            }))

        # Línea 2: IVA soportado
        if not float_is_zero(tax, precision_rounding=currency.rounding):
            debit_tax = abs(tax) if not is_refund else 0.0
            credit_tax = 0.0 if not is_refund else abs(tax)

            line_vals.append((0, 0, {
                "account_id": self.tax_account_id.id,
                "name": "IVA Soportado",
                "debit": debit_tax,
                "credit": credit_tax,
                "partner_id": move.partner_id.id,
                "currency_id": currency.id,
                "exclude_from_invoice_tab": True,
            }))

        # Línea 3: Proveedor (cuenta a pagar)
        if not float_is_zero(total, precision_rounding=currency.rounding):
            debit_total = 0.0 if not is_refund else abs(total)
            credit_total = abs(total) if not is_refund else 0.0

            line_vals.append((0, 0, {
                "account_id": payable_account.id,
                "name": move.ref or "A pagar proveedor",
                "debit": debit_total,
                "credit": credit_total,
                "partner_id": move.partner_id.id,
                "currency_id": currency.id,
                "exclude_from_invoice_tab": True,
            }))

        return line_vals

    def _validate_amounts_match(self, move, expected_untaxed, expected_tax, expected_total):
        """
        Valida que los importes calculados por Odoo coincidan con los esperados.

        Args:
            move: account.move record
            expected_untaxed: base esperada
            expected_tax: IVA esperado
            expected_total: total esperado

        Returns:
            tuple (success: bool, error_message: str)
        """
        currency = move.currency_id
        precision = currency.rounding
        tolerance = 0.01

        # Comparar importes
        untaxed_diff = abs(move.amount_untaxed - expected_untaxed)
        tax_diff = abs(move.amount_tax - expected_tax)
        total_diff = abs(move.amount_total - expected_total)

        errors = []

        if untaxed_diff > tolerance:
            errors.append(
                f"Base: esperado {expected_untaxed:.2f}, "
                f"obtenido {move.amount_untaxed:.2f} (diff: {untaxed_diff:.2f})"
            )

        if tax_diff > tolerance:
            errors.append(
                f"IVA: esperado {expected_tax:.2f}, "
                f"obtenido {move.amount_tax:.2f} (diff: {tax_diff:.2f})"
            )

        if total_diff > tolerance:
            errors.append(
                f"Total: esperado {expected_total:.2f}, "
                f"obtenido {move.amount_total:.2f} (diff: {total_diff:.2f})"
            )

        if errors:
            return False, " | ".join(errors)

        return True, ""

    def _process_csv_row(self, row_data, line_number):
        """
        Procesa una fila del CSV y crea la factura.

        Args:
            row_data: dict con los datos parseados
            line_number: número de línea

        Returns:
            tuple (success: bool, message: str, move_id: int or None)
        """
        ref = row_data.get("name", "?")
        try:
            # 1. Validar moneda
            currency_code = row_data["currency_id"]
            currency = self.env["res.currency"].search(
                [("name", "=", currency_code)], limit=1
            )
            if not currency:
                return False, f"Moneda '{currency_code}' no encontrada", None

            # 2. Validar y convertir importes
            amounts = self._validate_and_convert_amounts(
                row_data, line_number, currency
            )
            if not amounts:
                return False, "Error en importes (ver log)", None

            untaxed, tax, total = amounts

            # 3. Determinar move_type
            # Siempre crear facturas de compra
            if total >= 0:
                move_type = "in_invoice"
            else:
                move_type = "in_refund"
                # Para refunds, trabajamos con valores absolutos
                untaxed = abs(untaxed)
                tax = abs(tax)
                total = abs(total)

            # 4. Parsear fecha
            try:
                invoice_date = datetime.strptime(
                    row_data["invoice_date"], "%Y-%m-%d"
                ).date()
            except ValueError:
                return False, f"Fecha inválida: {row_data['invoice_date']}", None

            # 5. Obtener o crear proveedor
            partner = self._get_or_create_partner(row_data["partner_name"])

            # 6. Verificar duplicados
            if self._check_duplicate(ref, partner.id, invoice_date, move_type):
                return False, f"Duplicado: {ref}", None

            # 7. Cuenta a pagar
            payable_account = self.payable_account_id or partner.property_account_payable_id
            if not payable_account:
                return False, f"Proveedor '{partner.name}' sin cuenta a pagar configurada", None

            # 8. Crear factura (borrador)
            move_vals = {
                "move_type": move_type,
                "partner_id": partner.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "ref": ref,
                "journal_id": self.journal_id.id,
                "currency_id": currency.id,
                "company_id": self.company_id.id,
                "narration": f"Importado desde CSV Palmalube: {self.csv_filename or 'sin nombre'}",
            }

            # Crear con savepoint para rollback en caso de error
            with self.env.cr.savepoint():
                move = self.env["account.move"].create(move_vals)

                # 9. Crear líneas contables
                line_vals = self._create_invoice_lines(
                    move, untaxed, tax, total, currency, payable_account
                )

                move.write({"line_ids": line_vals})

                # 10. Validar importes
                move._compute_amount()
                success, error_msg = self._validate_amounts_match(
                    move, untaxed, tax, total
                )

                if not success:
                    raise ValidationError(f"Importes no cuadran: {error_msg}")

                if self.dry_run:
                    # En modo simulación, no commitear
                    raise ValidationError("Modo simulación - no crear factura")

                _logger.info(
                    f"Factura creada: {move.name} (ref: {ref}, "
                    f"partner: {partner.name}, total: {total})"
                )

                return True, f"Creada: {move.name}", move.id

        except ValidationError as e:
            # Errores controlados (modo simulación o validación)
            if self.dry_run:
                return True, f"[SIMULACIÓN] Validada OK: {ref}", None
            return False, str(e), None

        except Exception as e:
            _logger.exception(f"Error procesando línea {line_number}: {e}")
            return False, f"Error: {str(e)}", None

    def action_import_invoices(self):
        """Acción principal de importación."""
        self.ensure_one()

        if not self.csv_file:
            raise UserError(_("Debe seleccionar un archivo CSV"))

        # Decodificar CSV
        csv_data = base64.b64decode(self.csv_file)
        csv_string = csv_data.decode("utf-8")
        csv_stream = io.StringIO(csv_string)

        # Leer líneas
        lines = csv_stream.readlines()

        if not lines:
            raise UserError(_("El archivo CSV está vacío"))

        # Saltar cabecera
        if lines[0].strip().startswith("move_type"):
            lines = lines[1:]

        # Contadores
        total_rows = 0
        created_count = 0
        skipped_count = 0
        error_count = 0
        error_log = []
        created_moves = []

        # Procesar cada línea
        for idx, line in enumerate(lines, start=2):  # start=2 porque línea 1 es cabecera
            line = line.strip()
            if not line:
                continue

            total_rows += 1

            # Parsear línea
            row_data = self._parse_csv_line_robust(line, idx)

            if not row_data:
                error_count += 1
                error_log.append(f"Línea {idx}: error de parsing")
                continue

            # Procesar fila
            success, message, move_id = self._process_csv_row(row_data, idx)

            if success:
                if move_id:
                    created_count += 1
                    created_moves.append(move_id)
            else:
                if "Duplicado" in message:
                    skipped_count += 1
                    _logger.info(f"Línea {idx}: {message}")
                else:
                    error_count += 1
                    error_log.append(f"Línea {idx} (ref: {row_data.get('name', '?')}): {message}")

        # Construir mensaje de resultado
        result_lines = [
            "<h3>Resultado de la importación</h3>",
            f"<p><strong>Archivo:</strong> {self.csv_filename or 'sin nombre'}</p>",
            f"<p><strong>Filas procesadas:</strong> {total_rows}</p>",
            f"<p><strong>Facturas creadas:</strong> {created_count}</p>",
            f"<p><strong>Duplicados saltados:</strong> {skipped_count}</p>",
            f"<p><strong>Errores:</strong> {error_count}</p>",
        ]

        if self.dry_run:
            result_lines.append("<p><em>MODO SIMULACIÓN - No se han creado facturas</em></p>")

        if error_log:
            result_lines.append("<h4>Log de errores:</h4>")
            result_lines.append("<ul>")
            for error in error_log[:50]:  # Limitar a 50 errores
                result_lines.append(f"<li>{error}</li>")
            result_lines.append("</ul>")
            if len(error_log) > 50:
                result_lines.append(f"<p><em>... y {len(error_log) - 50} errores más</em></p>")

        result_html = "".join(result_lines)

        # Actualizar wizard
        self.write({
            "result_message": result_html,
            "total_rows": total_rows,
            "created_count": created_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "error_log": "\n".join(error_log) if error_log else "",
        })

        # Si hay facturas creadas, mostrar enlace
        if created_moves and not self.dry_run:
            return {
                "type": "ir.actions.act_window",
                "name": _("Facturas importadas"),
                "res_model": "account.move",
                "view_mode": "tree,form",
                "domain": [("id", "in", created_moves)],
                "context": {"create": False},
            }

        # Reabrir wizard con resultados
        return {
            "type": "ir.actions.act_window",
            "res_model": "import.invoice.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

