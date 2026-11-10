# PRD — registro-venta-micro (MVP Acotado)

> **Documento de Requisitos de Producto (PRD)**  
> **Versión:** 0.2.0-mvp  
> **Fecha:** 2026-11-10  
> **Estado:** Consolidado v0.2 Definitivo (Tras Auditoría y Resoluciones)  

---

## 1. Visión y Objetivos del Producto

### 1.1 Visión
Democratizar el punto de venta para micronegocios mediante una aplicación web progresiva (PWA) rápida y accesible desde cualquier smartphone o computadora, permitiendo cobrar al instante con múltiples medios de pago, actualizar el stock de forma automática y visualizar el margen de ganancia al cierre de la jornada en hora local.

### 1.2 Objetivos del MVP Acotado
1. **Cobro inmediato sin fricción:** Registrar ventas en pocos toques, calculando automáticamente el vuelto en efectivo y sin requerir aperturas de turnos de caja.
2. **Cero ventas duplicadas:** Garantizar idempotencia transaccional mediante UUID de cliente ante cualquier reintento de conexión.
3. **Múltiples medios de pago combinables:** Cobrar una venta repartida en efectivo, tarjeta y transferencias/QR.
4. **Actualización automática de stock:** Descontar inventario en la misma transacción de venta permitiendo saldo negativo transitorio sin trabar la venta.
5. **Claridad del margen diario en hora local:** Calcular automáticamente el margen de ganancia diario (`Ventas - Costos de referencia`) respetando la zona horaria del comercio (`timezone`).
6. **Aislamiento multitenant por motor:** Row Level Security (RLS) en PostgreSQL impidiendo fugas de datos entre comercios.

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
│ - Onboarding nuevo│ - Precios finales brutos   │ - Desglose por pago   │
│ - Tenant y RLS    │ - Cálculo vuelto efectivo  │ - Costo mercadería    │
│ - CRUD productos  │ - Descuento de stock en BD │ - Margen del día      │
│ - Precios, costo y│ - Efectivo/tarjeta/transf. │ - Agrupación por zona │
│   stock numérico  │ - Idempotencia por UUID    │   horaria del tenant  │
└───────────────────┴────────────────────────────┴───────────────────────┘
```

---

## 3. Especificación Detallada de Funcionalidades

### Épica 1: Entrada a Negocio y Catálogo (`E1-catalogo`)
- **US-01: Autenticación, Onboarding y Acceso al Negocio**
  - Autenticación con email y contraseña mediante Supabase Auth.
  - **Mecanismo de Onboarding (Patrón comprobado):** Si el usuario se autentica por primera vez y no posee un comercio asociado, la PWA le presenta un paso simple de bienvenida para ingresar el nombre de su comercio y país. Se envía a `POST /api/v1/auth/onboarding`, el cual crea la fila en `businesses` (con su `timezone` correspondiente al país) y asocia al usuario sin pedir credenciales nuevamente.
  - Todas las sesiones de base de datos configuran `SET LOCAL app.current_business_id` activando las políticas RLS.
- **US-02: Carga y Gestión Básica de Catálogo**
  - El dueño puede listar, crear y modificar productos de su negocio.
  - Cada producto almacena: código/SKU (opcional), nombre (obligatorio), precio de venta (`Decimal` > 0), costo unitario de referencia (`Decimal` >= 0) y stock numérico inicial (`Decimal` >= 0).

### Épica 2: Venta Transaccional e Idempotente (`E2-ventas`)
- **US-03: Registro de Venta con Múltiples Medios de Pago y Stock**
  - El dueño selecciona productos del catálogo armando el carrito en mostrador y totaliza la venta.
  - El dueño anuncia el monto total al comprador y registra los medios de pago (efectivo, tarjeta, transferencia/QR).
  - **Cálculo de vuelto en efectivo:** En pagos en efectivo, la interfaz permite ingresar el "Monto recibido" y calcula de forma inmediata el "Vuelto al cliente". El importe neto enviado al backend coincide exactamente con la venta.
  - **Precios brutos:** El sistema opera con precios finales brutos (sin desglose de impuestos en este MVP).
  - El cliente emite la venta con un `client_id` (UUID v4) persistido en el carrito para garantizar idempotencia incluso tras recargas de página.
  - **Actualización de stock transaccional:** En la misma transacción atómica de la venta, el backend ejecuta `UPDATE products SET stock = stock - :quantity WHERE id = :product_id AND business_id = :business_id`. La venta nunca se rechaza por stock insuficiente (permite stock negativo).
  - Si una petición se reintenta con el mismo `client_id`, el backend responde con la venta ya registrada sin duplicar registros ni volver a descontar stock.

### Épica 3: Reporte Final Diario (`E3-reportes`)
- **US-04: Reporte Diario de Ventas y Margen en Hora Local**
  - **Zona horaria del tenant:** La agrupación de ventas del día se calcula utilizando la zona horaria del comercio almacenada en la tabla `businesses` (ej. `America/Argentina/Buenos_Aires` según el país registrado):  
    `WHERE (created_at AT TIME ZONE b.timezone)::date = :report_date`
  - El dueño consulta en cualquier momento el reporte consolidado:
    - Total facturado bruto del día.
    - Desglose de ingresos por medio de pago (Total Efectivo, Total Tarjetas, Total Transferencias).
    - Cantidad total de transacciones completadas.
    - Costo de mercadería vendida acumulado en el día (sumando `quantity * unit_cost` congelado en `sale_items`).
    - Margen bruto estimado (`Total Facturado - Costo Total`) y porcentaje de ganancia sobre ventas (protegido contra división por cero cuando `Ventas = 0`).

---

## 4. Requisitos No Funcionales (NFR)

1. **Aislamiento Multitenant Fuerte:** RLS obligatoria en todas las tablas transaccionales en PostgreSQL (`USING (business_id = current_setting('app.current_business_id')::uuid)`).
2. **Precisión Financiera:** Prohibición estricta de tipos `float`. Uso exclusivo de `Decimal` (Python) y `numeric(12, 2)` (PostgreSQL).
3. **Idempotencia:** Toda petición de creación de venta requiere `client_id` UUID persistente por venta.
4. **Zona Horaria del Comercio:** Fechas almacenadas en `timestamptz` (UTC) y agrupadas por `timezone` de la organización para evitar quiebres de día en ventas nocturnas.
5. **Arquitectura:** Monolito modular (FastAPI backend + Vite/React frontend) desplegado en un único entorno productivo.

---

## 5. Decisiones Explícitas de Exclusión (Post-MVP)

- ❌ Sin apertura ni cierre de sesiones de caja (`cash_sessions`).
- ❌ Sin arqueo de caja (ciego ni estándar).
- ❌ Sin anulaciones de venta / notas de crédito en interfaz (errores se corrigen en mostrador antes de confirmar).
- ❌ Sin motor impositivo o cálculo de impuestos (IVA/tasas).
- ❌ Sin gestión de empleados, cajeros ni roles diferenciados (usuario único: Dueño del comercio).
- ❌ Sin asistente de IA en lenguaje natural.
- ❌ Sin multi-negocio dinámico ni invitaciones por correo.
- ❌ Sin sincronización offline compleja multi-pestaña.
