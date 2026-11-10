# Backlog Priorizado y Grafo de Dependencias — registro-venta-micro (MVP)

> **Ciclo:** it-project-orchestrator (stories-to-tickets)  
> **Fecha:** 2026-11-09  
> **Alcance:** MVP Acotado a 3 funcionalidades principales (Auth/Catálogo, Venta Multimedio, Reporte Diario)  

---

## 1. Grafo de Dependencias Técnicas

```mermaid
flowchart TD
    classDef default fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#ffffff,font-size:14px;
    classDef db fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ffffff,font-size:14px;
    classDef fe fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#ffffff,font-size:14px;

    T01["T01: Auth & Sesión Tenant"]
    T02["T02: Login UI & Storage"]:::fe
    T03["T03: BD Catálogo & RLS"]:::db
    T04["T04: API Catálogo REST"]
    T05["T05: Vista Catálogo"]:::fe
    T06["T06: BD Ventas & RLS"]:::db
    T07["T07: Servicio Venta Idempotente"]
    T08["T08: Mostrador & Cobro Multimedio"]:::fe
    T09["T09: Endpoint Reporte Diario"]
    T10["T10: Vista Reporte Diario"]:::fe

    T01 --> T02
    T01 --> T03
    T03 --> T04
    T04 --> T05
    T03 --> T06
    T06 --> T07
    T05 --> T08
    T07 --> T08
    T06 --> T09
    T09 --> T10
```

### Leyenda de Colores
- 🟩 Base de Datos (`PostgreSQL` · Esquemas, Migraciones Alembic y RLS)
- 🟦 Backend (`FastAPI` · Endpoints y Servicios)
- 🟪 Frontend (`React / PWA` · Vistas y Componentes)

---

## 2. Secuencia de Implementación por Fases

| Fase | Tickets | Capa | Trabajo en Paralelo |
|---|---|---|---|
| **Fase 1: Fundación y Auth** | `TICKET-01`<br>`TICKET-02` | Backend<br>Frontend | Una vez listo T01, T02 y T03 se pueden abordar en paralelo. |
| **Fase 2: Catálogo Básico** | `TICKET-03`<br>`TICKET-04`<br>`TICKET-05` | Base de datos<br>Backend<br>Frontend | T03 habilita el esquema de catálogo y las tablas de ventas. |
| **Fase 3: Núcleo Transaccional de Ventas** | `TICKET-06`<br>`TICKET-07`<br>`TICKET-08` | Base de datos<br>Backend<br>Frontend | Corazón del sistema: cobro multimedio, recálculo `Decimal` e idempotencia. |
| **Fase 4: Reporte Diario y Margen** | `TICKET-09`<br>`TICKET-10` | Backend<br>Frontend | Consume las ventas registradas para calcular totales y rentabilidad. |

---

## 3. T-shirt Sizing y Matriz de Riesgo

| Ticket | Título | Capa | Talla | Riesgo | Justificación Técnica |
|---|---|---|:---:|:---:|---|
| **TICKET-01** | Auth, Onboarding & Sesión Tenant | Backend | **M** | Medio | Supabase Auth, endpoint `/onboarding` para creación de comercio con `timezone` y RLS. |
| **TICKET-02** | Pantalla Login & Onboarding en PWA | Frontend | **S** | Bajo | Formulario de credenciales con paso simple de bienvenida para usuario nuevo. |
| **TICKET-03** | Esquema Catálogo con RLS y Stock | Database | **S** | Bajo | Tabla `products` con columnas `sale_price`, `cost_price` y `stock` (`numeric(12,2)`). |
| **TICKET-04** | API REST Catálogo de Productos | Backend | **M** | Bajo | CRUD estándar con esquemas Pydantic `Decimal` (precios brutos sin impuestos). |
| **TICKET-05** | Vista de Catálogo en PWA | Frontend | **M** | Bajo | Grilla táctil reactiva con buscador y stock visible. |
| **TICKET-06** | Esquema Ventas & Idempotencia RLS | Database | **M** | Medio | Tablas `sales`, `sale_items`, `payments` y clave única de idempotencia `(business_id, client_id)`. |
| **TICKET-07** | Servicio Venta Idempotente & Stock | Backend | **L** | Medio | Transacción ACID: recálculo `Decimal`, descuento atómico de stock (permite negativo) y respuesta idempotente. |
| **TICKET-08** | Mostrador, Vuelto en Efectivo & Cobro | Frontend | **L** | Medio | UI táctil de carrito, calculador de vuelto en efectivo y UUID persistido en carrito. |
| **TICKET-09** | Endpoint Reporte Diario en Hora Local | Backend | **M** | Bajo | Agregaciones SQL por fecha local (`timezone`), cálculo de margen bruto y protección división por cero. |
| **TICKET-10** | Vista de Reporte Diario | Frontend | **S** | Bajo | Pantalla con KPIs visuales y desglose por medio de pago. |

---

## 4. Matriz Impacto vs. Complejidad

```
 ALTO  │
       │  [Quick Wins ⭐]               [Proyectos Clave]
       │  ⭐ T01 (Auth & Onboarding)     T07 (Venta Idempotente + Stock)
       │  ⭐ T03 (Esquema Catálogo)      T08 (Mostrador con Vuelto FE)
       │  ⭐ T09 (Reporte en Hora Local) T06 (Esquema Ventas RLS)
IMPACTO│
       ├─────────────────────────────────────────────────────────────
       │  [Tareas Menores]              [Evaluar / Descartables]
       │  T02 (Login/Onboarding UI FE)  (Notas de crédito - POST-MVP)
       │  T04 (API Catálogo BE)         (Arqueos y sesiones - POST-MVP)
       │  T05 (Catálogo UI FE)          (IA Assistant - POST-MVP)
       │  T10 (Reporte UI FE)           (Motor de impuestos - POST-MVP)
 BAJO  │
       └─────────────────────────────────────────────────────────────
          BAJA                        COMPLEJIDAD               ALTA
```

- **Quick Wins (⭐):** `T01`, `T03` y `T09` entregan alto valor inmediato con bajo esfuerzo.
- **Ruta Crítica:** `T01` → `T03` → `T06` → `T07` → `T08`.
