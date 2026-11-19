# 🔬 REPORTE DE MUTATION TESTING FRONTEND: issue-40-login-onboarding-frontend

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS BLINDADOS]`
- **Worktree Auditado:** `C:\Users\Armenta\Documents\Repositories\wt-40-login-onboarding-sesion` (ejecución aislada sobre copia temporal tras refuerzo de `frontend-qa-agent`; árbol vivo `frontend/src` y `frontend/src/test` intacto)
- **Tests Auditados:**
  - `frontend/src/test/auth/login.test.tsx` (12 tests)
  - `frontend/src/test/auth/onboarding.test.tsx` (9 tests)
  - `frontend/src/test/auth/session.test.tsx` (8 tests)
  - `frontend/src/test/auth/ui-catalog.test.tsx` (7 tests)
  - Baseline ejecutado sobre `src/test/auth/`: `4` archivos, `36/36` tests en verde (`50.75s`; `41/41` en suite completa reportada tras refuerzo + Gate 4 con `0` advertencias).
- **Tasa de Mutantes Eliminados:** `19/19` (`100%`)

---

## 2. Matriz de Mutaciones Evaluadas (FM1–FM5)

| ID | Familia | Mutación Aplicada (Copia Aislada) | Archivo Mutado | Archivo de Test que Atrapa | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|---|
| `FM1-A` | FM1 (Logic/Validation Inversion) | Desactiva validación de formato de email (`!EMAIL_PATTERN.test(normalizedEmail)` → `false`) en `validateLoginInput` | `frontend/src/features/auth/validation.ts` (L39) | `frontend/src/test/auth/login.test.tsx` (L89) | Sí | 🗑 Eliminado |
| `FM1-B` | FM1 (Logic/Validation Inversion) | Desactiva validación de longitud máxima (`> 100`) en `validateOnboardingInput` | `frontend/src/features/auth/validation.ts` (L71) | `frontend/src/test/auth/onboarding.test.tsx` (L109) | Sí | 🗑 Eliminado |
| `FM2-A` | FM2 (Session/Storage Security) | Persiste `access_token` JWT simulado dentro de `localStorage` en `writePublicAuthContext` | `frontend/src/features/auth/storage.ts` (L87) | `frontend/src/test/auth/session.test.tsx` (L86) | Sí | 🗑 Eliminado |
| `FM2-B` | FM2 (Network Error Bypass) | Ignora fallo de red en `performFetch` devolviendo `Response` HTTP `200` `{}` en lugar de lanzar `ApiNetworkError` | `frontend/src/lib/api-client.ts` (L66–68) | `frontend/src/test/auth/login.test.tsx` (L303) | Sí | 🗑 Eliminado |
| `FM2-C` | FM2 (Session Security Bypass) | Ante `401` en `/me` + `/refresh` en `resolveSessionFromServer`, retorna `readPublicAuthContext()` sin limpiar `localStorage` | `frontend/src/features/auth/AuthContext.tsx` (L57–60) | `frontend/src/test/auth/session.test.tsx` (L167) | Sí | 🗑 Eliminado |
| `FM2-D` | FM2 (Network Fallback Bypass) | Elimina fallback a contexto público cacheado ante `ApiNetworkError` en `resolveSessionFromServer` | `frontend/src/features/auth/AuthContext.tsx` (L61–66) | `frontend/src/test/auth/session.test.tsx` (L238) | Sí | 🗑 Eliminado |
| `FM3-A` | FM3 (Handler/Action Removal) | Desconecta `onSubmit={handleSubmit}` en `LoginContainer` reemplazándolo por no-op (`event.preventDefault()`) | `frontend/src/features/auth/containers/LoginContainer.tsx` (L114) | `frontend/src/test/auth/login.test.tsx` (L81) | Sí | 🗑 Eliminado |
| `FM3-B` | FM3 (Handler/Action Removal) | Desconecta `onLogout={handleLogout}` en `CounterShellContainer` (estado `authenticated`) | `frontend/src/features/auth/containers/CounterShellContainer.tsx` (L68) | `frontend/src/test/auth/session.test.tsx` (L216) | Sí | 🗑 Eliminado |
| `FM3-C` | FM3 (Handler/Action Removal) | Desconecta `onLogout` en `OnboardingContainer` (`onLogout={undefined}`), eliminando botón/acción `"Cerrar sesión"` en onboarding | `frontend/src/features/auth/containers/OnboardingContainer.tsx` (L121) | `frontend/src/test/auth/onboarding.test.tsx` (L343) | Sí | 🗑 Eliminado |
| `FM4-A` | FM4 (A11y/Role Degradation) | Degrada `role="dialog"` a `role="presentation"` y elimina `aria-modal="true"` en `OnboardingModal` | `frontend/src/features/auth/components/OnboardingModal.tsx` (L74–75) | `frontend/src/test/auth/login.test.tsx` (L206) | Sí | 🗑 Eliminado |
| `FM4-B` | FM4 (A11y/Role Degradation) | Degrada `role="alert"` a `role="presentation"` en `ErrorAlert` | `frontend/src/shared/ui/ErrorAlert.tsx` (L18) | `frontend/src/test/auth/login.test.tsx` (L81) | Sí | 🗑 Eliminado |
| `FM4-C` | FM4 (A11y/Role Degradation) | Elimina texto de feedback dentro de `ErrorAlert` (`{message}` → `{""}`) manteniendo `role="alert"` | `frontend/src/shared/ui/ErrorAlert.tsx` (L29) | `frontend/src/test/auth/login.test.tsx` (L235) | Sí | 🗑 Eliminado |
| `FM4-D` | FM4 (A11y/Role Degradation) | Elimina atributo `aria-pressed={isDark}` en `ThemeToggleButton` | `frontend/src/shared/ui/ThemeToggleButton.tsx` (L15) | `frontend/src/test/auth/login.test.tsx` (L151) | Sí | 🗑 Eliminado |
| `FM4-E` | FM4 (A11y/Feedback Degradation) | Colapsa `mapLoginErrorMessage` a `"Error"` fijo ignorando `401`, `422`, `429`, `502`, `503` y `ApiNetworkError` | `frontend/src/features/auth/containers/LoginContainer.tsx` (L15–38) | `frontend/src/test/auth/login.test.tsx` (L235) | Sí | 🗑 Eliminado |
| `FM5-A` | FM5 (API Error Masking) | Enmascara respuestas `401`/`409`/`422` como éxito en `apiFetch` (`!response.ok && ![401, 409, 422].includes(response.status)`) | `frontend/src/lib/api-client.ts` (L113) | `frontend/src/test/auth/login.test.tsx` (L235) | Sí | 🗑 Eliminado |
| `FM5-B` | FM5 (API Error Masking) | Enmascara `409` en `onboardingRequest` devolviendo `BusinessResponse` falso | `frontend/src/features/auth/api.ts` (L17–23) | `frontend/src/test/auth/onboarding.test.tsx` (L225) | Sí | 🗑 Eliminado |
| `FM5-C` | FM5 (API Error Masking - 422) | Enmascara respuestas `422` como éxito en `apiFetch` (`!response.ok && response.status !== 422`) | `frontend/src/lib/api-client.ts` (L113) | `frontend/src/test/auth/login.test.tsx` (L282) | Sí | 🗑 Eliminado |
| `FM5-D` | FM5 (API Error Masking - Login) | Enmascara `401` y `422` en `loginRequest` devolviendo `{}` como éxito falso | `frontend/src/features/auth/api.ts` (L9–15) | `frontend/src/test/auth/login.test.tsx` (L235) | Sí | 🗑 Eliminado |
| `FM5-E` | FM5 (API Error Masking - Onboarding 422) | Enmascara `422` en `onboardingRequest` devolviendo `BusinessResponse` falso | `frontend/src/features/auth/api.ts` (L17–23) | `frontend/src/test/auth/onboarding.test.tsx` (L321) | Sí | 🗑 Eliminado |

### Resumen por Categoría Canónica
- **FM1 (Logic/Validation Inversion):** `2/2` eliminados (`100%`)
- **FM2 (Session/Storage Security & Network Error Bypass):** `4/4` eliminados (`100%`)
- **FM3 (Handler/Action Removal):** `3/3` eliminados (`100%`)
- **FM4 (A11y/Role Degradation):** `5/5` eliminados (`100%`)
- **FM5 (API Error Masking):** `5/5` eliminados (`100%`)

---

## 3. Brechas de Falsabilidad y Acción Requerida

- **Sin brechas activas (`0` mutantes vivos).** Las 4 brechas detectadas en la pasada inicial (`12/19` → `63.2%`) fueron cerradas tras el refuerzo ejecutado por `frontend-qa-agent`:
  1. **Feedback de error específico en login (`FM2-B`, `FM4-E`, `FM5-C`, `FM5-D`):** `frontend/src/test/auth/login.test.tsx` (L235, L282, L303) y `frontend/src/test/auth/ui-catalog.test.tsx` (L126) validan ahora el texto esperado dentro de `role="alert"` para `401`, `422`, `429`, `502`, `503` y error de red, eliminando falsos positivos por `TypeError` accidental.
  2. **Logout dentro del flujo de onboarding (`FM3-C`):** `frontend/src/test/auth/onboarding.test.tsx` (L327–350) ejercita `"Cerrar sesión"` dentro de `role="dialog"`, validando `POST /api/v1/auth/logout`, limpieza de `localStorage` y navegación a `/login`.
  3. **Error HTTP `422` en `/onboarding` (`FM5-E`):** `frontend/src/test/auth/onboarding.test.tsx` (L297–325) verifica que `422` mantiene el modal abierto en `/` y muestra el mensaje en `role="alert"`.
  4. **Resiliencia ante error de red en `GET /me` (`FM2-D`):** `frontend/src/test/auth/session.test.tsx` (L222–242) confirma preservación del contexto público cacheado cuando `GET /api/v1/auth/me` falla por error de red.
- *Observación operativa (no bloqueante):* En el primer arranque en frío de la copia temporal, el primer test de `onboarding.test.tsx` (L48) rozó el timeout de `1000ms` de `findByRole("dialog")` mientras se compilaba el chunk `React.lazy` de `OnboardingContainer` (`1218ms` en frío vs `1277ms` en caliente); todas las ejecuciones posteriores con caché cálida y las pruebas mutadas corrieron de forma determinista.
