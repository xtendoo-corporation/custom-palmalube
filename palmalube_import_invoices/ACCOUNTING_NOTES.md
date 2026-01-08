# NOTAS CONTABLES - Palmalube Import Invoices

## Supuestos y decisiones contables

### 1. Estructura de asientos

El módulo crea facturas de proveedor con **3 líneas contables básicas**:

#### Ejemplo: Factura de 121€ (base 100€ + IVA 21€)

```
DEBE        | CUENTA                    | HABER
------------|---------------------------|----------
100,00      | 600000 - Compras          |
21,00       | 472000 - IVA Soportado    |
            | 400000 - Proveedores      | 121,00
```

#### Ejemplo: Abono de 121€ (base 100€ + IVA 21€)

```
DEBE        | CUENTA                    | HABER
------------|---------------------------|----------
            | 600000 - Compras          | 100,00
            | 472000 - IVA Soportado    | 21,00
121,00      | 400000 - Proveedores      |
```

### 2. Motor de impuestos

**El módulo NO usa el motor de impuestos de Odoo.**

Motivos:
- Los datos vienen de un sistema externo que ya ha calculado los importes
- Puede haber tipos impositivos especiales (ej: 4%, 10%, 21%, exentos)
- Puede haber importes efectivos que no corresponden a porcentajes exactos
- La prioridad es cuadrar exactamente con el CSV, no recalcular

**Consecuencias**:
- No se crean registros `account.tax` asociados a las líneas
- Los importes de IVA no aparecerán en informes fiscales automáticos
- Los libros de IVA requerirán tratamiento especial

### 3. Validación de importes

El módulo aplica **dos niveles de validación**:

#### Nivel 1: Validación CSV
```python
base + IVA = total (±0.02€ de tolerancia)
```

Si no cuadra en el CSV, la fila se rechaza.

#### Nivel 2: Validación Odoo
```python
move.amount_untaxed == csv.amount_untaxed (±0.01€)
move.amount_tax == csv.amount_tax (±0.01€)
move.amount_total == csv.amount_total (±0.01€)
```

Si Odoo calcula importes diferentes tras crear el asiento, se hace rollback.

### 4. Precisión decimal

Todo el procesamiento usa `Decimal` de Python para evitar errores de punto flotante.

```python
from decimal import Decimal, ROUND_HALF_UP

untaxed = Decimal("100.00")
tax = Decimal("21.00")
total = untaxed + tax  # 121.00 exacto
```

El redondeo se aplica según la moneda:
- EUR: 2 decimales
- JPY: 0 decimales
- etc.

### 5. Cuentas contables

El módulo requiere **3 cuentas configurables**:

#### Cuenta de Gastos (expense_account_id)
- **Uso**: Base imponible
- **Tipo**: Gastos (`expense`, `expense_depreciation`, `expense_direct_cost`)
- **Ejemplo**: 600000 - Compras

**Limitación**: Todas las bases van a la misma cuenta. Si necesitas diferentes cuentas según el tipo de gasto (material, servicios, etc.), deberás:
1. Hacer una importación por tipo
2. O modificar las facturas manualmente después

#### Cuenta de IVA Soportado (tax_account_id)
- **Uso**: Importe del IVA
- **Tipo**: Cualquier tipo (normalmente `asset_current`)
- **Ejemplo**: 472000 - IVA Soportado

**Nota**: Esta cuenta no está vinculada a ningún impuesto de Odoo, es una cuenta contable "manual".

#### Cuenta a Pagar (payable_account_id)
- **Uso**: Deuda con el proveedor
- **Tipo**: `liability_payable`
- **Ejemplo**: 400000 - Proveedores

**Flexibilidad**:
- Puede dejarse vacía → usa la del proveedor
- O especificar una cuenta común para todos

### 6. Gestión de abonos (refunds)

Cuando `amount_total < 0`, se crea automáticamente un `in_refund`.

**Importante**: Los importes se guardan en **valor absoluto**:

```python
# CSV: -100, -21, -121
# Odoo crea:
move_type = "in_refund"
amount_untaxed = 100.00  # positivo
amount_tax = 21.00       # positivo
amount_total = 121.00    # positivo
```

Los signos contables (debe/haber) se invierten automáticamente.

### 7. Conversión de tipos de movimiento

El CSV puede traer cualquier `move_type`, pero el módulo **siempre crea facturas de compra**:

```python
if total >= 0:
    move_type = "in_invoice"  # Factura de proveedor
else:
    move_type = "in_refund"   # Abono de proveedor
```

**Motivo**: El módulo está diseñado para importar facturas de proveedor (cuentas a pagar), no facturas de cliente.

### 8. Multi-empresa

El módulo soporta multi-empresa:
- Todas las búsquedas filtran por `company_id`
- Los proveedores pueden ser compartidos o específicos de la empresa
- Los diarios y cuentas deben ser de la empresa seleccionada

### 9. Multi-moneda

El módulo soporta cualquier moneda activa en Odoo:
- La moneda debe existir y estar activa
- Los importes se redondean según la precisión de la moneda
- No se hacen conversiones (los importes son tal cual en el CSV)

### 10. Limitaciones conocidas

#### No hay líneas de producto
Las facturas se crean **sin productos** (`invoice_line_ids` vacío).

Solo hay líneas contables (`line_ids`).

**Consecuencia**: No se puede hacer análisis por producto ni categoría.

**Alternativa**: Si necesitas productos, deberás modificar el módulo para añadir un campo `product_id` al CSV y crear `invoice_line_ids`.

#### No hay registro de impuestos
No se usan objetos `account.tax`.

**Consecuencia**: Los informes fiscales estándar de Odoo no incluirán estas facturas.

**Alternativa**:
1. Crear informes personalizados basados en las cuentas contables
2. O modificar el módulo para asignar impuestos "ficticios" (requiere lógica adicional)

#### Una sola cuenta de gasto
Todas las bases van a la misma cuenta.

**Alternativa**:
1. Hacer múltiples importaciones con diferentes cuentas
2. O modificar el módulo para añadir un campo `account_code` al CSV

#### Sin líneas de detalle
Cada factura es un solo importe global (base + IVA).

Si el CSV original tiene múltiples líneas por factura, deberás agregarlo previamente.

### 11. Casos especiales

#### IVA = 0
Funciona correctamente. Se crea una línea con importe 0.

#### Base negativa + IVA negativo = Total negativo
Se convierte en `in_refund` con todos los importes en positivo.

#### Base positiva + IVA negativo (o viceversa)
**No se valida**. Si la suma cuadra, se acepta.

Podrías tener casos raros como:
- Base: 150€
- IVA: -30€
- Total: 120€

El módulo lo aceptará si cuadra matemáticamente.

#### Importes con más de 2 decimales
Se redondean según la moneda (normalmente 2 decimales para EUR).

### 12. Flujo de aprobación

Las facturas se crean en **estado borrador** (`draft`).

**No se contabilizan automáticamente**.

El usuario debe:
1. Revisar las facturas importadas
2. Validarlas manualmente (o con un workflow)
3. Contabilizarlas

**Motivo**: Permitir revisión antes de impactar contablemente.

### 13. Duplicados

La detección de duplicados se basa en:

```python
(ref, partner_id, invoice_date, move_type)
```

**No se valida** que los importes coincidan.

Ejemplo:
- ST001, Proveedor A, 2025-12-30, in_invoice, 121€ → OK
- ST001, Proveedor A, 2025-12-30, in_invoice, 500€ → DUPLICADO (mismo ref+partner+fecha+tipo)

Si necesitas reimportar con importes corregidos, debes eliminar la factura anterior.

### 14. Trazabilidad

Cada factura creada incluye en el campo `narration`:

```
Importado desde CSV Palmalube: nombre_archivo.csv
```

Esto permite identificar el origen de la factura.

### 15. Rollback y transaccionalidad

El módulo usa **savepoints** por fila:

```python
with self.env.cr.savepoint():
    # Crear factura
    # Si falla, rollback solo de esta fila
```

**Ventajas**:
- Una fila mala no impide importar las demás
- Errores individuales se registran en el log

**Limitación**:
- No hay rollback global (no puedes "deshacer" toda la importación)

### 16. Rendimiento

Para importaciones grandes (>1000 filas):
- El módulo procesa línea por línea (sin batch)
- Cada factura hace un commit individual
- Tiempo estimado: ~0.5-1s por factura

**Recomendaciones**:
- Para >5000 facturas, considerar partir el CSV
- Ejecutar en horarios de bajo uso

## Conclusión

Este módulo prioriza:
1. **Exactitud**: Los importes cuadran al céntimo
2. **Robustez**: Parsing flexible del CSV
3. **Trazabilidad**: Logs claros de errores

Está diseñado para casos donde:
- Los datos vienen de un sistema externo fiable
- Los importes ya están calculados
- Se necesita control manual antes de contabilizar

No es adecuado si:
- Necesitas recalcular impuestos según reglas de Odoo
- Necesitas líneas de producto con análisis
- Necesitas integración automática con informes fiscales

Para esos casos, deberás extender el módulo o usar el importador estándar de Odoo con productos e impuestos.

