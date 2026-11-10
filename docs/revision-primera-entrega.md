# AI4DEVS · LIDR · Revisión de la Primera Entrega

**Proyecto:** registro-venta-micro  
**Alumno:** Nindirí Armenta Guerrero  
**Repositorio:** ninargue/registro-venta-micro  
**Fecha de Revisión:** 2 de noviembre de 2026  
**Calificación general:** LUZ AMARILLA — AVANZAR AJUSTANDO

---

## 1. Resumen y Veredicto

> «registro-venta-micro» propone una PWA para que un micronegocio registre sus ventas en pocos toques desde el celular, incluso sin conexión, y para que el dueño vea caja, stock y margen sin hardware dedicado. El diseño nace del mostrador: la venta nunca se rechaza ni por falta de señal ni por falta de stock, el aislamiento entre negocios lo impone PostgreSQL y no el código, y la IA se queda fuera de las cifras. La propuesta está muy bien encaminada; la única reserva es de **alcance**, porque el primer lote reúne más piezas de las que una sola persona puede tener listas a la vez.

---

## 2. Estado de la Documentación

- **Ficha del proyecto:** Completa. Multidispositivo, multitenant y offline.
- **Objetivo del producto:** Completo. Descuadres de caja, stock a ojo, margen invisible. Roles: dueño y cajero.
- **Funcionalidades principales:** Completa pero extensa. Requiere acotar.
- **Diagrama de arquitectura:** Completo. Monolito modular con PWA offline-first y matriz de trade-offs.
- **Componentes principales:** Completo. Falta nombrar el proveedor del LLM.
- **Modelo de datos:** Completo. Claves compuestas con negocio y RLS.
- **Entidades principales:** Completo. Concurrencia de stock e índices razonados.
- **Especificación API (OpenAPI):** Completo en lo crítico, pero faltan rutas de: iniciar sesión/elegir negocio, abrir caja, descargar catálogo offline y consulta de asistente.
- **Historias de usuario:** Completo en flujos principales. Falta historia de alta de negocio y carga inicial de catálogo.
- **Tickets de trabajo:** Muy sólidos (BD, backend y frontend). Estimaciones algo optimistas en concurrencia offline y RLS.

---

## 3. El Problema y el Alcance del MVP: Recomendaciones Clave

### Lo que queda como Núcleo del MVP (3 Funcionalidades Principales):
1. **Entrada a un negocio y catálogo básico:**
   - Inicio de sesión y selección de negocio.
   - Carga y consulta de catálogo básico de productos.
2. **Venta con varios medios de pago:**
   - Venta transaccional e idempotente con totales recalculados en servidor.
   - Varios medios de pago (efectivo, tarjeta, transferencia).
   - Enfoque: PWA online primero e idempotente, posterior cola offline.
3. **Cierre de caja con arqueo y reporte del día:**
   - Apertura y cierre de caja con declaración de efectivo esperado vs. contado.
   - Reporte diario de ventas y margen del día para el dueño.

### Lo que queda Fuera de Alcance (Post-MVP / Ampliación):
- ❌ Asistente en lenguaje natural con IA.
- ❌ Cambio entre múltiples negocios en la misma sesión e invitaciones por email.
- ❌ Detección de reuso de refresh token rotativo encima de Supabase Auth (usar sesión estándar primero).
- ❌ Anulaciones de ventas (el modelo ya las contempla, pero no implementarlas en la UI del MVP).
- ❌ Ambientes separados de staging y producción (un solo ambiente publicado basta).
- ❌ Facturación electrónica, lectura de facturas con IA (OCR), imágenes de producto, impresión térmica y sincronización incremental.

---

## 4. Cabos por Cerrar antes de Programar (Arquitectura)

1. **Apertura de caja sin conexión:**
   - Definir si abrir caja exige conexión (lo más simple) o si entra en la cola antes de las ventas.
   - Completar las rutas faltantes en OpenAPI: `/auth/login`, `/auth/select-business`, `/cajas/abrir`, `/catalogo/offline`.
2. **ADR y Diccionario de datos:**
   - Escribir los ADRs citados (o quitar referencias huérfanas en plantillas de PR/prompts).
   - Alinear campos del modelo de datos con el diagrama y listas de tablas.
3. **CLAUDE.md del proyecto:**
   - Commitear las reglas de oro: dinero en `Decimal` (nunca float), negocio sale del token y nunca del body, un ticket a la vez, tests contra BD real con RLS.
