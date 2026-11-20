# 🔬 REPORTE DE MUTATION TESTING FRONTEND: us-04-t10-reporte-diario-frontend

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS BLINDADOS]`
- **Tests Auditados:**
  - `frontend/src/features/reports/utils/formatters.test.ts`
  - `frontend/src/features/reports/components/DailyReportView.test.tsx`
  - `frontend/src/features/reports/pages/DailyReportPage.test.tsx`
  - (`frontend/src/app/router.test.tsx` y `frontend/src/test/mocks/*` no se ejercitaron: ningún mutante tocó router ni mocks)
- **Tasa de Mutantes Eliminados:** `14/14` (`100%`)
- **Mutantes vivos:** 0. En la primera ejecución sobrevivieron `FM1-c` y `FM1-e` (12/14, 85.7%). Tras el refuerzo de `formatters.test.ts` y `DailyReportView.test.tsx`, se re-ejecutaron ambos y quedaron eliminados.

### Metodología y aislamiento
- Los mutantes se aplicaron sobre una **copia temporal aislada** de `frontend/` en el directorio scratchpad de la sesión. Esa copia tiene `node_modules` instalado con `npm ci` y se restauró desde el árbol vivo tras cada mutante.
- El árbol vivo (`frontend/`) **no se modificó**. Tras la ejecución, `diff -rq` entre el árbol vivo y la copia (sin `node_modules`) no mostró diferencias en ficheros fuente.
- No se ejecutó ningún comando `git`: lo prohíben las invariantes del agente. Por eso el `git checkout --` y el `git status` pedidos en el encargo se sustituyeron por copia aislada y `diff`. La verificación final de árbol limpio con `git status` debe hacerla el agente orquestador.
- Por mutante se ejecutó solo la suite afectada con `npx vitest run <archivos>`. La línea base de las 3 suites estaba en verde (18/18 tests).
- Se ejecutaron 14 mutantes, algo por encima del objetivo de ~10, porque cada ejecución tardaba segundos.
- **FM2 (cola offline):** este cambio es de solo lectura y no usa `<offline_store>`. FM2 se adaptó a su análogo en este módulo: pérdida del filtro de fecha en la petición y en la clave de caché.

## 2. Matriz de Mutaciones Evaluadas
| ID | Mutación | Archivo mutado | Archivo de Test | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|
| FM1-a | Se elimina el redondeo half-up en `calculatePaymentSharePercentage` | `utils/formatters.ts` | `formatters.test.ts`, `DailyReportView.test.tsx`, `DailyReportPage.test.tsx` | Sí (16.67% pasa a 16.66%) | 🗑 Eliminado |
| FM1-b | `parseDecimalCents` pierde el signo negativo | `utils/formatters.ts` | `formatters.test.ts`, `DailyReportView.test.tsx` | Sí (`-$250,00`, `-25.00%`) | 🗑 Eliminado |
| FM1-c | Guarda `totalSalesCents <= 0n` debilitada a `< 0n` (división por cero si total=0 y método>0) | `utils/formatters.ts` | `formatters.test.ts`, `DailyReportView.test.tsx`, `DailyReportPage.test.tsx` | Sí en re-ejecución (`RangeError: Division by zero`, test "total_sales 0.00 y monto de método positivo no lanza"). Primera ejecución: No | 🗑 Eliminado (re-ejecución) |
| FM1-d | Estado `empty` nunca se activa (`transactions_count === 0` pasa a `=== -1`) | `pages/DailyReportPage.tsx` | `DailyReportPage.test.tsx` | Sí (escenario día sin ventas) | 🗑 Eliminado |
| FM1-e | Detección de margen negativo invertida (`< 0n` pasa a `> 0n`) en KpiGrid | `components/DailyReportKpiGrid.tsx` | `DailyReportView.test.tsx`, `DailyReportPage.test.tsx` | Sí en re-ejecución (`toHaveClass("text-error")` falla en "negative gross margin" y `not.toHaveClass` en "positive gross margin"). Primera ejecución: No | 🗑 Eliminado (re-ejecución) |
| FM2-a | Filtro de fecha ignorado: `fetchDailyReport` omite `?date=` | `api/reportsApi.ts` | `DailyReportPage.test.tsx` | Sí (`requestedDates` esperado `[null,"2026-11-18"]`) | 🗑 Eliminado |
| FM2-b | `queryKey` sin la fecha (caché compartida entre fechas) | `hooks/useDailyReport.ts` | `DailyReportPage.test.tsx` | Sí (escenario cambio de fecha) | 🗑 Eliminado |
| FM3-a | `handleDateChange` no actualiza `searchParams` | `pages/DailyReportPage.tsx` | `DailyReportPage.test.tsx` | Sí | 🗑 Eliminado |
| FM3-b | `handleRetry` vacío (no hace `refetch`) | `pages/DailyReportPage.tsx` | `DailyReportPage.test.tsx` | Sí (escenario error y recuperación) | 🗑 Eliminado |
| FM3-c | `onClick` de "Reintentar" desconectado en la vista | `components/DailyReportView.tsx` | `DailyReportView.test.tsx`, `DailyReportPage.test.tsx` | Sí (`onRetry` llamado 0 veces) | 🗑 Eliminado |
| FM4-a | Se elimina `role="alert"` del bloque de error | `components/DailyReportView.tsx` | `DailyReportView.test.tsx`, `DailyReportPage.test.tsx` | Sí (`getByRole("alert")`) | 🗑 Eliminado |
| FM4-b | Se elimina el texto de feedback "Sin ventas registradas..." | `components/DailyReportView.tsx` | `DailyReportView.test.tsx`, `DailyReportPage.test.tsx` | Sí | 🗑 Eliminado |
| FM5-a | Error HTTP enmascarado como éxito (`!response.ok` pasa a `false`) | `api/reportsApi.ts` | `DailyReportPage.test.tsx` | Sí (el alert 403 nunca aparece) | 🗑 Eliminado |
| FM5-b | El mensaje del servidor se sustituye por el genérico | `api/reportsApi.ts` | `DailyReportPage.test.tsx` | Sí (se asegura el mensaje del backend) | 🗑 Eliminado |

## 3. Brechas de Falsabilidad y Acción Requerida

Sin brechas abiertas. No se requiere acción adicional de `frontend-qa-agent`.

### Re-ejecución acotada de mutantes vivos (tras refuerzo de tests)
- **Aislamiento:** copia temporal de `frontend/` en el scratchpad de la sesión, con `node_modules` enlazado por symlink desde el árbol vivo (solo lectura). Cada mutante se aplicó con `sed` y se restauró desde un `.orig`. Al terminar, `diff -rq` entre `frontend/src` y la copia no mostró diferencias. No se tocaron tests, código productivo ni `<openapi_path>`. No se ejecutó ningún comando `git`.
- **Línea base de la copia:** 6 archivos y 27 tests en verde.
- **FM1-c (`totalSalesCents <= 0n` pasa a `< 0n`):** 🗑 Eliminado. Falla `formatters.test.ts` > "con total_sales 0.00 y monto de método positivo no lanza y devuelve 0.00%" con `RangeError: Division by zero` (1 test fallido, 19 en verde). El test nuevo `calculatePaymentSharePercentage("100.00", "0.00")` ejercita la guarda, y el caso `"-5.00"` cubre total negativo.
- **FM1-e (`isNegativeMargin` pasa de `< 0n` a `> 0n`):** 🗑 Eliminado. Fallan 2 tests de `DailyReportView.test.tsx`: "positive gross margin" (`not.toHaveClass("text-error")`) y "negative gross margin" (`toHaveClass("text-error")`). Con ello el énfasis visual del margen negativo queda afirmado.
- **Tasa final:** 14/14 eliminados (100%).

### Observaciones (no bloqueantes)
- Cobertura sólida de FM2 (fecha en query y clave de caché), FM3 (handlers de fecha y reintento), FM4 (rol `alert` y texto de feedback) y FM5 (error HTTP y mensaje del servidor).
- Sin aserciones vacías ni mocks que oculten payloads de error.
- Los resultados de los 12 mutantes eliminados en la primera ejecución se conservan sin cambios. La suite solo se reforzó, y la línea base sigue en verde.
