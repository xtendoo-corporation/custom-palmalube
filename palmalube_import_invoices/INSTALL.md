# INSTALACIÓN RÁPIDA - Palmalube Import Invoices

## 1. Actualizar el repositorio custom-palmalube

```bash
cd /home/xtendoo/Documentos/odoo/18verifactu/odoo/custom/src/custom-palmalube/
git add palmalube_import_invoices/
git commit -m "Add palmalube_import_invoices module"
```

## 2. Reiniciar Odoo (si está usando Docker)

```bash
cd /home/xtendoo/Documentos/odoo/18verifactu/
docker-compose restart odoo
```

O si está ejecutando Odoo manualmente:

```bash
# Detener el proceso actual de Odoo y reiniciarlo
```

## 3. Instalar el módulo en Odoo

1. Acceder a Odoo con usuario administrador
2. Ir a **Aplicaciones**
3. Activar el **Modo Desarrollador**:
   - Menú → Ajustes → Activar modo desarrollador
4. Clic en **Actualizar lista de aplicaciones**
5. Buscar: `palmalube_import_invoices`
6. Clic en **Instalar**

## 4. Configuración inicial

Antes de usar el módulo, asegúrate de tener:

### Diario de compras

1. Ir a **Contabilidad → Configuración → Diarios**
2. Verificar que existe un diario de tipo "Compras"
3. Si no existe, crear uno:
   - Nombre: "Facturas de Proveedor"
   - Tipo: Compras
   - Código: BILL

### Cuentas contables

Verificar que existen estas cuentas (o identificar las equivalentes):

1. **Cuenta de Gastos** (para la base imponible):
   - Tipo: Gastos
   - Ejemplo: 600000 - Compras

2. **Cuenta de IVA Soportado**:
   - Tipo: Activo corriente
   - Ejemplo: 472000 - IVA Soportado

3. **Cuenta a Pagar**:
   - Tipo: Pasivo a pagar
   - Ejemplo: 400000 - Proveedores

## 5. Uso básico

1. Ir a **Contabilidad → Proveedores → Importación Palmalube**

2. Configurar el wizard:
   - Subir archivo CSV
   - Seleccionar diario
   - Seleccionar cuenta de gastos
   - Seleccionar cuenta de IVA
   - Marcar "Crear proveedores si no existen"
   - (Opcional) Marcar "Modo simulación" para probar sin crear facturas

3. Clic en **Importar**

4. Revisar el resultado y las facturas creadas

## 6. Probar con CSV de ejemplo

Hay un CSV de prueba en:
```
palmalube_import_invoices/tests/test_invoices.csv
```

Descargarlo y probarlo en el wizard.

## 7. Ejecutar tests (opcional)

Para verificar que todo funciona correctamente:

```bash
docker-compose run --rm odoo odoo --test-enable --stop-after-init \
  --log-level=test -d devel -i palmalube_import_invoices
```

O si usas Odoo en local:

```bash
odoo-bin -c /path/to/odoo.conf --test-enable --stop-after-init \
  --log-level=test -d devel -i palmalube_import_invoices
```

## 8. Troubleshooting

### El módulo no aparece en la lista

**Solución**:
1. Verificar que el módulo está en la ruta correcta
2. Actualizar lista de aplicaciones (modo desarrollador)
3. Buscar por "palmalube" o "import"

### Error al instalar: "No such file or directory"

**Solución**:
- Verificar permisos de los archivos
- Reiniciar el servidor Odoo

### Error: "Cuenta a pagar no configurada"

**Solución**:
- Configurar cuenta a pagar en el proveedor
- O seleccionar una cuenta a pagar por defecto en el wizard

## Contacto

Soporte: soporte@xtendoo.es

