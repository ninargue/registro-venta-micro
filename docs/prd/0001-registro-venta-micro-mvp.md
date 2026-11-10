# PRD — registro-venta-micro (MVP Acotado)

> **Documento de Requisitos de Producto (PRD)**  
> **Versión:** 1.0.0-mvp  
> **Fecha:** 2026-11-09  
> **Estado:** Consolidado (Sin sesiones de caja ni descuento de stock)  

---

## 1. Visión y Objetivos del Producto

### 1.1 Visión
Democratizar el punto de venta para micronegocios mediante una aplicación web progresiva (PWA) rápida y accesible desde cualquier dispositivo, permitiendo cobrar al instante con múltiples medios de pago y visualizar el margen de ganancia al cierre de la jornada sin complejidades operativas.

### 1.2 Objetivos del MVP Acotado
1. **Cobro inmediato sin fricción:** Registrar ventas en pocos toques sin requerir pasos previos de apertura de turnos ni bloqueos de caja.
2. **Cero ventas duplicadas:** Garantizar idempotencia transaccional mediante UUID de cliente ante cualquier reintento de conexión.
3. **Múltiples medios de pago combinables:** Cobrar una venta repartida en efectivo, tarjeta y transferencias/QR.
4. **Claridad del margen diario:** Calcular automáticamente el margen de ganancia diario (`Ventas - Costos de referencia`).
5. **Aislamiento multitenant por motor:** Row Level Security (RLS) en PostgreSQL impidiendo fugas de datos entre comercios.

---

## 2. Épicas y Módulos del MVP

```
┌────────────────────────────────────────────────────────────────────────┐
│                        registro-venta-micro                            │
├───────────────────┬────────────────────────────┬───────────────────────┤
│   Épica 1: Auth   │      Épica 2: Ventas       │    Épica 3: Reporte   │
│    y Catálogo     │    Multimedio de Pago      │     Final Diario      │
├───────────────────┼────────────────────────────┼───────────────────────┤
│ - Login / Acceso  │ - Carrito de venta ágil    │ - Facturación total   │
│ - Tenant activo   │ - Cálculo exacto en server │ - Desglose por pago   │
│ - CRUD productos  │ - Efectivo/tarjeta/transf. │ - Costo mercadería    │
│ - Precios y costo │ - Idempotencia por UUID    │ - Margen del día      │
│ - Stock referencial│ - Venta directa y libre   │ - Tickets emitidos    │
└───────────────────┴────────────────────────────┴───────────────────────┘
```

---

## 3. Especificación Detallada de Funcionalidades

### Épica 1: Entrada a Negocio y Catálogo (`E1-catalogo`)
- **US-01: Autenticación y Acceso al Negocio**
  - Autenticación mediante email y contraseña con Supabase Auth.
  - El backend resuelve el `business_id` del usuario autenticado. Todas las sesiones de base de datos configuran `SET LOCAL app.current_business_id` activando las políticas RLS.
- **US-02: Carga y Gestión Básica de Catálogo**
  - El dueño puede listar, dar de alta y editar productos de su negocio.
  - Cada producto almacena: código/SKU (opcional), nombre (obligatorio), precio de venta (`Decimal` > 0), costo unitario de referencia (`Decimal` >= 0) y stock referencial.

### Épica 2: Venta Transaccional e Idempotente (`E2-ventas`)
- **US-03: Registro de Venta con Múltiples Medios de Pago**
  - El cajero selecciona productos del catálogo armando el carrito.
  - Se especifican los medios de pago aplicados (efectivo, tarjeta, transferencia/QR) cuya suma debe coincidir exactamente con el total recalculado por el servidor.
  - El cliente emite la venta con un `client_id` (UUID v4) como clave de idempotencia.
  - **Venta directa:** No requiere sesión de caja previa; la venta se asocia directamente al `business_id` y al usuario autenticado.
  - El servidor recalcula subtotales e impuestos en `Decimal`, graba la venta (`sale`), sus líneas (`sale_items`) congelando precio y costo unitario, y los pagos (`payments`) en una sola transacción atómica.
  - **Sin deducción de stock:** La venta no modifica inventario en tiempo real en este MVP.
  - Si una petición se reintenta con el mismo `client_id`, el backend responde con la venta ya registrada sin duplicar registros.

### Épica 3: Reporte Final Diario (`E3-reportes`)
- **US-04: Reporte Diario de Ventas y Margen**
  - El dueño consulta en cualquier momento el reporte consolidado de la fecha actual:
    - Total facturado bruto del día.
    - Desglose de ingresos por medio de pago: Total Efectivo, Total Tarjetas, Total Transferencias.
    - Cantidad total de transacciones / tickets completados.
    - Costo de mercadería vendida acumulado en el día (sumatoria de `quantity * unit_cost` congelado en `sale_items`).
    - Margen bruto estimado (`Total Facturado - Costo Total`) y porcentaje de ganancia sobre ventas.

---

## 4. Requisitos No Funcionales (NFR)

1. **Aislamiento Multitenant Fuerte:** RLS obligatoria en todas las tablas transaccionales en PostgreSQL (`USING (business_id = current_setting('app.current_business_id')::uuid)`).
2. **Precisión Financiera:** Prohibición estricta de tipos de coma flotante (`float`) para montos monetarios. Uso exclusivo de `Decimal` (Python) y `numeric(12, 2)` (PostgreSQL).
3. **Idempotencia:** Toda petición de creación de venta requiere `client_id` UUID único por negocio.
4. **Arquitectura:** Monolito modular (FastAPI backend + Vite/React frontend) desplegado en un único entorno productivo.

---

## 5. Decisiones Explícitas de Exclusión (Post-MVP)

- ❌ Sin apertura ni cierre de sesiones de caja (`cash_sessions`).
- ❌ Sin arqueo de caja (ciego ni estándar).
- ❌ Sin descuento de stock en tiempo real / Kardex.
- ❌ Sin asistente de IA en lenguaje natural.
- ❌ Sin multi-negocio ni invitaciones por correo.
- ❌ Sin anulaciones de venta en interfaz de usuario.
- ❌ Sin sincronización offline compleja multi-pestaña.
