# Registro de Decisiones de Arquitectura (ADR)

Este directorio documenta las decisiones de arquitectura y diseño del proyecto **registro-venta-micro**, siguiendo el formato unificado basado en [0000-plantilla-adr.md](0000-plantilla-adr.md).

## Convenciones de Registro
- Cada decisión arquitectónica o de diseño estructural se registra en un archivo `NNNN-titulo-en-kebab-case.md`.
- Los ADRs nunca se eliminan; si una decisión es reemplazada, se marca su estado como `Reemplazado por ADR-XXXX` y se documenta el nuevo ADR.
- Redacción a nivel arquitectónico y conceptual, evitando nombres volátiles de variables o rutas internas de funciones.

---

## Índice de Decisiones

| Número | Título | Estado | Fecha | Issue / PR |
| :---: | :--- | :---: | :---: | :---: |
| [ADR-0001](0001-rol-runtime-y-endurecimiento-rls.md) | Aislamiento multitenant mediante rol de runtime y RLS estricto | Aceptado | 2026-11-16 | #39, #55 / PR #52 |
| [ADR-0002](0002-sesion-httponly-y-refresh-stateless.md) | Gestión de sesión mediante cookies HttpOnly y renovación sin estado | Aceptado | 2026-11-17 | #39, #55 / PR #52 |
| [ADR-0003](0003-contrato-uniforme-errores-y-resiliencia-auth.md) | Contrato uniforme de respuestas de error y resiliencia en autenticación | Aceptado | 2026-11-17 | #39, #55 / PR #52 |
| [ADR-0004](0004-esquema-productos-stock-negativo-y-unicidad-parcial.md) | Modelo de catálogo, stock flexible con saldo negativo y unicidad por tenant | Aceptado | 2026-11-18 | #42, #55 / PR #57 |
| [ADR-0005](0005-sincronizacion-contractual-openapi-y-prevencion-drift.md) | Sincronización contractual de API mediante OpenAPI estático y validación en CI | Aceptado | 2026-11-18 | #56 / PR #58 |
| [ADR-0006](0006-simulacion-api-frontend-msw-red.md) | Simulación de API en pruebas de cliente a nivel de red con MSW en modo estricto | Aceptado | 2026-11-18 | #56 / PR #58 |
| [ADR-0007](0007-sistema-diseno-tokens-tailwind-v4-theme.md) | Sistema de diseño ergonómico para POS y tokens semánticos con Tailwind CSS v4 `@theme` | Aceptado | 2026-11-18 | #56 / PR #58 |
