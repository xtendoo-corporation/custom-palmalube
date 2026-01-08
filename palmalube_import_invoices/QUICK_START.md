# 🚀 GUÍA RÁPIDA - Palmalube Import Invoices

## ⚡ INSTALACIÓN EXPRESS (3 minutos)

### 1. Reiniciar Odoo
```bash
cd /home/xtendoo/Documentos/odoo/18verifactu/
docker-compose restart odoo
```

### 2. Instalar módulo
1. Odoo → **Aplicaciones**
2. Activar **Modo Desarrollador**
3. **Actualizar lista de aplicaciones**
4. Buscar: `palmalube_import_invoices`
5. **Instalar**

### 3. Usar
**Contabilidad → Proveedores → Importación Palmalube**

---

## 📋 CSV MÍNIMO PARA PROBAR

Crear archivo `test.csv`:
```csv
move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST001,2025-12-30,Proveedor Test,100.00,21.00,121.00,draft,EUR
```

---

## ⚙️ CONFIGURACIÓN WIZARD

| Campo | Ejemplo | Requerido |
|-------|---------|-----------|
| CSV | Subir archivo | ✅ |
| Compañía | Tu compañía | ✅ |
| Diario | Facturas de proveedor | ✅ |
| Cuenta Gastos | 600000 - Compras | ✅ |
| Cuenta IVA | 472000 - IVA Soportado | ✅ |
| Cuenta a Pagar | Dejar vacío (usa del proveedor) | ❌ |
| Crear proveedores | ✅ Marcar | - |
| Modo simulación | ⬜ Desmarcar (primera vez) | - |

---

## ✅ CASOS SOPORTADOS

### ✓ Partner con coma SIN comillas
```csv
out_invoice,ST001,2025-12-30,RYME WORLDWIDE, S.A.,221.50,0.00,221.50,draft,EUR
```

### ✓ Partner entrecomillado
```csv
out_invoice,ST002,2025-12-30,"S.P. AUTO REISEN, S.L.",547.40,38.32,585.72,draft,EUR
```

### ✓ Abono (importes negativos)
```csv
out_invoice,ST003,2025-12-30,Proveedor X,-100.00,-21.00,-121.00,draft,EUR
```
Se convierte automáticamente en `in_refund`

---

## 🐛 ERRORES COMUNES

| Error | Causa | Solución |
|-------|-------|----------|
| "Moneda EUR no encontrada" | Moneda no activa | Contabilidad → Configuración → Monedas → Activar EUR |
| "Proveedor sin cuenta a pagar" | Proveedor sin configurar | Configurar cuenta en proveedor O usar cuenta por defecto en wizard |
| "Importes no cuadran" | base + IVA ≠ total | Revisar CSV, debe cumplir: 100 + 21 = 121 |
| "Módulo no aparece" | No actualizada lista | Modo desarrollador → Actualizar lista |

---

## 🧪 TESTING RÁPIDO

```bash
# Test completo (10 tests)
docker-compose run --rm odoo odoo --test-enable --stop-after-init \
  --log-level=test -d devel -i palmalube_import_invoices
```

Resultado esperado: `✓ 10/10 tests PASSED`

---

## 📊 RESULTADO DE IMPORTACIÓN

Tras importar verás:
- ✅ **Filas procesadas**: Total de líneas
- ✅ **Facturas creadas**: Cuántas se crearon
- ⏭️ **Duplicados saltados**: Ya existían
- ❌ **Errores**: Con detalle de línea y causa

---

## 🔍 VALIDACIONES AUTOMÁTICAS

### Nivel CSV
- base + IVA = total (±0.02€)

### Nivel Odoo
- Importes calculados = CSV (±0.01€)
- Moneda existe y activa
- Proveedor existe o se crea
- No duplicado (ref + partner + fecha + tipo)

---

## 💡 TIPS

### Modo simulación
Primera vez: **Marcar "Modo simulación"** para validar sin crear.

### Cuenta a pagar
Dejar **vacío** para usar la cuenta del proveedor (recomendado).

### Crear proveedores
**Marcar** si los proveedores pueden no existir.

### Duplicados
Si necesitas reimportar: **Elimina la factura anterior** antes.

---

## 📚 DOCUMENTACIÓN COMPLETA

- **README.md**: Documentación exhaustiva
- **INSTALL.md**: Guía de instalación paso a paso
- **ACCOUNTING_NOTES.md**: Decisiones contables técnicas
- **RESUMEN_ENTREGABLE.md**: Checklist completo

---

## 📞 SOPORTE

**Email**: soporte@xtendoo.es

---

## ⏱️ TIEMPO ESTIMADO

- Instalación: **2-3 minutos**
- Primera importación: **1 minuto**
- Importación masiva: **~1 segundo por factura**

---

**Desarrollado por Xtendoo - Odoo 18.0**

