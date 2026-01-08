# Palmalube Import Invoices

## Descripción

Módulo para importar facturas de proveedor desde archivos CSV con validación contable exacta.

### Características principales

- **Parsing robusto de CSV**: Maneja correctamente nombres de proveedores con comas (entrecomillados o sin comillas)
- **Validación contable precisa**: Garantiza que base + IVA = total al céntimo (tolerancia ±0.01€)
- **Creación automática de proveedores**: Opción para crear proveedores nuevos si no existen
- **Detección de duplicados**: Evita importar facturas duplicadas (ref + partner + fecha + tipo)
- **Modo simulación**: Opción dry-run para validar el CSV sin crear facturas
- **Gestión de abonos**: Convierte automáticamente importes negativos en facturas rectificativas (in_refund)

## Formato del CSV

### Estructura

El archivo CSV debe tener la siguiente cabecera:

```
move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
```

### Campos

- **move_type**: Tipo de movimiento original (se ignora, siempre se crean facturas de compra)
- **name**: Referencia del proveedor (se guarda en el campo `ref`)
- **invoice_date**: Fecha de factura (formato: YYYY-MM-DD)
- **partner_name**: Nombre del proveedor (puede contener comas)
- **amount_untaxed**: Base imponible
- **amount_tax**: Importe del IVA
- **amount_total**: Total de la factura
- **state**: Estado (se ignora, todas se crean en borrador)
- **currency_id**: Código de la moneda (ej: EUR, USD)

### Ejemplos

```csv
move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST 005371,2025-12-30,RYME WORLDWIDE, S.A.,221.50,0.00,221.50,draft,EUR
out_invoice,ST 005372,2025-12-30,"S.P. AUTO REISEN, S.L.",547.40,38.32,585.72,draft,EUR
out_invoice,ST 005373,2025-12-30,AUTOMOVILES Y TRACTORES, SOCIEDAD ANONIMA,500.00,105.00,605.00,draft,EUR
out_invoice,ST 005374,2025-12-30,Proveedor Normal,100.00,21.00,121.00,draft,EUR
out_invoice,ST 005375,2025-12-30,Abono Proveedor,-100.00,-21.00,-121.00,draft,EUR
```

**Nota importante**: El campo `partner_name` puede contener comas. El parser es robusto y funciona tanto si el campo está entrecomillado como si no lo está.

## Instalación

1. Clonar o copiar el módulo en el directorio de addons:
   ```bash
   cd /path/to/odoo/custom/src/custom-palmalube/
   git pull  # o copiar manualmente
   ```

2. Actualizar la lista de módulos en Odoo:
   - Ir a **Aplicaciones**
   - Activar el **Modo Desarrollador**
   - Clic en **Actualizar lista de aplicaciones**

3. Buscar e instalar el módulo:
   - Buscar "Palmalube Import Invoices"
   - Clic en **Instalar**

## Uso

### Acceso

Desde el menú de Odoo:

**Contabilidad → Proveedores → Importación Palmalube**

### Configuración del wizard

1. **Archivo CSV**: Seleccionar el archivo CSV a importar

2. **Configuración contable**:
   - **Compañía**: Seleccionar la compañía (por defecto: compañía actual)
   - **Diario**: Diario de compras donde se crearán las facturas
   - **Cuenta de Gasto (Base)**: Cuenta contable para la base imponible
   - **Cuenta de IVA Soportado**: Cuenta contable para el IVA soportado
   - **Cuenta a Pagar (Opcional)**: Dejar en blanco para usar la cuenta del proveedor

3. **Opciones**:
   - **Crear proveedores si no existen**: Si está marcado, crea automáticamente proveedores nuevos
   - **Modo simulación (dry-run)**: Si está marcado, valida el CSV sin crear facturas

4. Clic en **Importar**

### Resultados

Tras la importación, el wizard muestra:

- **Filas procesadas**: Total de líneas del CSV procesadas
- **Facturas creadas**: Número de facturas creadas correctamente
- **Duplicados saltados**: Facturas que ya existían
- **Errores**: Número de errores encontrados
- **Log de errores**: Detalle de los errores por línea

Si se crearon facturas (y no estamos en modo simulación), se abre automáticamente una vista con las facturas importadas.

## Lógica de conversión

### Tipo de factura

- Si `amount_total >= 0`: Se crea como **factura de proveedor** (in_invoice)
- Si `amount_total < 0`: Se crea como **abono de proveedor** (in_refund)

Nota: Aunque el CSV diga `out_invoice`, siempre se crean facturas de compra.

### Gestión de proveedores

1. Busca el proveedor por nombre (case-insensitive, normalizando espacios)
2. Si existe, lo usa (y marca como proveedor si no lo era)
3. Si no existe:
   - Si "Crear proveedores" está activado: crea el proveedor nuevo
   - Si no: genera error

### Detección de duplicados

Se considera duplicado si ya existe una factura con:
- Misma referencia (`ref`)
- Mismo proveedor (`partner_id`)
- Misma fecha (`invoice_date`)
- Mismo tipo (`move_type`)

Los duplicados se saltan automáticamente (no generan error).

### Validación de importes

El módulo valida que:

```
amount_untaxed + amount_tax = amount_total (±0.01€)
```

Tras crear la factura, se verifica que los importes calculados por Odoo coincidan exactamente con los del CSV (tolerancia máxima: 0.01€).

Si no cuadran, la factura no se crea y se registra el error.

## Aspectos contables

### Estructura de asientos

Para cada factura se crean 3 líneas contables:

1. **Línea de gasto** (base imponible):
   - Cuenta: expense_account_id
   - Debe: amount_untaxed (si in_invoice)
   - Haber: amount_untaxed (si in_refund)

2. **Línea de IVA soportado**:
   - Cuenta: tax_account_id
   - Debe: amount_tax (si in_invoice)
   - Haber: amount_tax (si in_refund)

3. **Línea de proveedor** (a pagar):
   - Cuenta: payable_account_id o cuenta del proveedor
   - Haber: amount_total (si in_invoice)
   - Debe: amount_total (si in_refund)

### Precisión decimal

Todos los cálculos se realizan usando `Decimal` de Python y se redondean según la precisión de la moneda (normalmente 2 decimales para EUR).

### Limitaciones

- **No calcula impuestos**: El módulo NO usa el motor de impuestos de Odoo. Los importes de IVA vienen del CSV.
- **Sin líneas de producto**: Las facturas se crean solo con líneas contables (no hay invoice_line_ids con productos).
- **Una sola cuenta de gasto**: Todas las bases se imputan a la misma cuenta de gasto configurada.

## Tests

El módulo incluye 10 tests unitarios que validan:

1. Importar partner con coma SIN comillas
2. Importar partner entrecomillado con coma
3. Importar con importes negativos (crea in_refund)
4. Detección de duplicados
5. Modo simulación (dry-run)
6. Moneda inválida genera error
7. Importes que no cuadran generan error
8. Creación de proveedores nuevos
9. Partner con múltiples comas
10. Partner complejo sin comillas

### Ejecutar tests

```bash
odoo-bin -c /path/to/odoo.conf -d test_db -i import_invoices_palmalube --test-enable --stop-after-init --log-level=test
```

O solo los tests de este módulo:

```bash
odoo-bin -c /path/to/odoo.conf -d test_db --test-tags /import_invoices_palmalube
```

## Troubleshooting

### Error: "Proveedor sin cuenta a pagar configurada"

**Solución**:
1. Ir a **Contactos → Proveedores**
2. Buscar el proveedor
3. Ir a la pestaña **Contabilidad**
4. Configurar la **Cuenta a pagar**

O bien, en el wizard seleccionar una **Cuenta a Pagar** por defecto.

### Error: "Importes no cuadran"

**Causas posibles**:
- Los importes del CSV no suman correctamente (base + IVA ≠ total)
- Diferencias de redondeo superiores a 0.01€

**Solución**: Revisar los importes en el CSV y corregir si es necesario.

### Error: "Moneda no encontrada"

**Solución**: Activar la moneda en Odoo:
1. Ir a **Contabilidad → Configuración → Monedas**
2. Buscar la moneda (ej: EUR)
3. Activarla si está desactivada

### Los proveedores se crean duplicados

**Causa**: El nombre en el CSV tiene espacios extras o mayúsculas/minúsculas diferentes.

**Solución**: El módulo normaliza nombres, pero para evitar duplicados se recomienda:
- Usar nombres consistentes en el CSV
- Revisar los proveedores antes de importar
- Usar "Crear proveedores" solo si es necesario

## Soporte

Para bugs o mejoras, contactar con:
- **Email**: soporte@xtendoo.es
- **GitHub**: https://github.com/xtendoo-corporation

## Licencia

AGPL-3.0

## Autor

Xtendoo - 2026

