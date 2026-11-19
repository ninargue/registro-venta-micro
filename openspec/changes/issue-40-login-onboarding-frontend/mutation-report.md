# 🔬 REPORTE DE MUTATION TESTING FRONTEND: issue-40-login-onboarding-frontend

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS COMPLACIENTES DETECTADOS]`
- **Worktree Auditado:** `C:\Users\Armenta\Documents\Repositories\wt-40-login-onboarding-sesion` (ejecución aislada sobre copia temporal; árbol vivo `frontend/src` y `frontend/src/test` intacto)
- **Tests Auditados:**
  - `frontend/src/test/auth/login.test.tsx` (12 tests)
  - `frontend/src/test/auth/onboarding.test.tsx` (7 tests)
  - `frontend/src/test/auth/session.test.tsx` (7 tests)
  - `frontend/src/test/auth/ui-catalog.test.tsx` (7 tests)
  - Baseline ejecutado: `npx vitest run src/test/auth/` → 4 archivos, 33/33 tests en verde (`37.39s`).
- **Tasa de Mutantes Eliminados:** `12/19` (`63.2%`)

---

## 2. Matriz de Mutaciones Evaluadas (FM1–FM5)

| ID | Familia | Mutación Aplicada (Copia Aislada) | Archivo Mutado | Archivo de Test que Atrapa / Evalúa | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|---|
| `FM1-A` | FM1 (Logic/Validation Inversion) | Desactiva validación de formato de email (`!EMAIL_PATTERN.test(normalizedEmail)` → `false`) en `validateLoginInput` | `frontend/src/features/auth/validation.ts` (L39) | `frontend/src/test/auth/login.test.tsx` (L89) | Sí | 🗑 Eliminado |
| `FM1-B` | FM1 (Logic/Validation Inversion) | Desactiva validación de longitud máxima (`> 100`) en `validateOnboardingInput` | `frontend/src/features/auth/validation.ts` (L71) | `frontend/src/test/auth/onboarding.test.tsx` (L109) | Sí | 🗑 Eliminado |
| `FM2-A` | FM2 (Session/Storage Security) | Persiste `access_token` JWT simulado dentro de `localStorage` en `writePublicAuthContext` | `frontend/src/features/auth/storage.ts` (L87) | `frontend/src/test/auth/session.test.tsx` (L86) | Sí | 🗑 Eliminado |
| `FM2-B` | FM2 (Network Error Bypass) | Ignora fallo de red en `performFetch` devolviendo `Response` HTTP `200` `{}` en lugar de lanzar `ApiNetworkError` | `frontend/src/lib/api-client.ts` (L66–68) | `frontend/src/test/auth/` (33/33 pasan, exit `0`) | **No** | 🧟 Vivo |
| `FM2-C` | FM2 (Session Security Bypass) | Ante `401` en `/me` + `/refresh` en `resolveSessionFromServer`, retorna `readPublicAuthContext()` sin limpiar `localStorage` | `frontend/src/features/auth/AuthContext.tsx` (L57–60) | `frontend/src/test/auth/session.test.tsx` (L167) | Sí | 🗑 Eliminado |
| `FM2-D` | FM2 (Network Fallback Bypass) | Elimina fallback a contexto público cacheado ante `ApiNetworkError` en `resolveSessionFromServer` | `frontend/src/features/auth/AuthContext.tsx` (L61–66) | `frontend/src/test/auth/` (33/33 pasan, exit `0`) | **No** | 🧟 Vivo |
| `FM3-A` | FM3 (Handler/Action Removal) | Desconecta `onSubmit={handleSubmit}` en `LoginContainer` reemplazándolo por no-op (`event.preventDefault()`) | `frontend/src/features/auth/containers/LoginContainer.tsx` (L114) | `frontend/src/test/auth/login.test.tsx` (L81) | Sí | 🗑 Eliminado |
| `FM3-B` | FM3 (Handler/Action Removal) | Desconecta `onLogout={handleLogout}` en `CounterShellContainer` (estado `authenticated`) | `frontend/src/features/auth/containers/CounterShellContainer.tsx` (L68) | `frontend/src/test/auth/session.test.tsx` (L216) | Sí | 🗑 Eliminado |
| `FM3-C` | FM3 (Handler/Action Removal) | Desconecta `onLogout` en `OnboardingContainer` (`onLogout={undefined}`), eliminando botón/acción `"Cerrar sesión"` en onboarding | `frontend/src/features/auth/containers/OnboardingContainer.tsx` (L121) | `frontend/src/test/auth/` (33/33 pasan, exit `0`) | **No** | 🧟 Vivo |
| `FM4-A` | FM4 (A11y/Role Degradation) | Degrada `role="dialog"` a `role="presentation"` y elimina `aria-modal="true"` en `OnboardingModal` | `frontend/src/features/auth/components/OnboardingModal.tsx` (L74–75) | `frontend/src/test/auth/login.test.tsx` (L206) | Sí | 🗑 Eliminado |
| `FM4-B` | FM4 (A11y/Role Degradation) | Degrada `role="alert"` a `role="presentation"` en `ErrorAlert` | `frontend/src/shared/ui/ErrorAlert.tsx` (L18) | `frontend/src/test/auth/login.test.tsx` (L81) | Sí | 🗑 Eliminado |
| `FM4-C` | FM4 (A11y/Role Degradation) | Elimina texto de feedback dentro de `ErrorAlert` (`{message}` → `{""}`) manteniendo `role="alert"` | `frontend/src/shared/ui/ErrorAlert.tsx` (L29) | `frontend/src/test/auth/ui-catalog.test.tsx` (L126) | Sí | 🗑 Eliminado |
| `FM4-D` | FM4 (A11y/Role Degradation) | Elimina atributo `aria-pressed={isDark}` en `ThemeToggleButton` | `frontend/src/shared/ui/ThemeToggleButton.tsx` (L15) | `frontend/src/test/auth/login.test.tsx` (L151) | Sí | 🗑 Eliminado |
| `FM4-E` | FM4 (A11y/Feedback Degradation) | Colapsa `mapLoginErrorMessage` a `"Error"` fijo ignorando `401`, `422`, `429`, `502`, `503` y `ApiNetworkError` | `frontend/src/features/auth/containers/LoginContainer.tsx` (L15–38) | `frontend/src/test/auth/` (33/33 pasan, exit `0`) | **No** | 🧟 Vivo |
| `FM5-A` | FM5 (API Error Masking) | Enmascara respuestas `401`/`409`/`422` como éxito en `apiFetch` (`!response.ok && ![401, 409, 422].includes(response.status)`) | `frontend/src/lib/api-client.ts` (L113) | `frontend/src/test/auth/session.test.tsx` (L169) | Sí | 🗑 Eliminado |
| `FM5-B` | FM5 (API Error Masking) | Enmascara `409` en `onboardingRequest` devolviendo `BusinessResponse` falso | `frontend/src/features/auth/api.ts` (L17–23) | `frontend/src/test/auth/onboarding.test.tsx` (L225) | Sí | 🗑 Eliminado |
| `FM5-C` | FM5 (API Error Masking - 422) | Enmascara respuestas `422` como éxito en `apiFetch` (`!response.ok && response.status !== 422`) | `frontend/src/lib/api-client.ts` (L113) | `frontend/src/test/auth/` (33/33 pasan, exit `0`) | **No** | 🧟 Vivo |
| `FM5-D` | FM5 (API Error Masking - Login) | Enmascara `401` y `422` en `loginRequest` devolviendo `{}` como éxito falso | `frontend/src/features/auth/api.ts` (L9–15) | `frontend/src/test/auth/` (33/33 pasan, exit `0`) | **No** | 🧟 Vivo |
| `FM5-E` | FM5 (API Error Masking - Onboarding 422) | Enmascara `422` en `onboardingRequest` devolviendo `BusinessResponse` falso | `frontend/src/features/auth/api.ts` (L17–23) | `frontend/src/test/auth/` (33/33 pasan, exit `0`) | **No** | 🧟 Vivo |

### Resumen por Categoría Canónica
- **FM1 (Logic/Validation Inversion):** `2/2` eliminados (`100%`)
- **FM2 (Session/Storage Security & Network Error Bypass):** `2/4` eliminados (`50%`) — **sobreviven `FM2-B` y `FM2-D`**
- **FM3 (Handler/Action Removal):** `2/3` eliminados (`66.7%`) — **sobrevive `FM3-C`**
- **FM4 (A11y/Role Degradation):** `4/5` eliminados (`80%`) — **sobrevive `FM4-E`**
- **FM5 (API Error Masking):** `2/5` eliminados (`40%`) — **sobreviven `FM5-C`, `FM5-D` y `FM5-E`**

---

## 3. Brechas de Falsabilidad y Acción Requerida

Se detectaron **7 mutantes vivos** agrupados en **4 brechas concretas de complacencia** que `frontend-qa-agent` (Paso 2) debe reforzar antes de re-verificar:

1. **Aserciones complacientes de `role="alert"` en errores de login (`FM2-B`, `FM4-E`, `FM5-C`, `FM5-D`):**
   - *Causa raíz:* En `frontend/src/test/auth/login.test.tsx` (L234–235, L261–262, L282) y `frontend/src/test/auth/ui-catalog.test.tsx` (L124–126), los tests únicamente verifican `expect(alert).toBeInTheDocument()` (o `textContent.length > 0` en el 401 de catálogo). Cuando `performFetch` devuelve un `200 {}` (`FM2-B`), `apiFetch` ignora un `422` (`FM5-C`) o `loginRequest` enmascara `401`/`422` devolviendo `{}` (`FM5-D`), `toPublicAuthContext(response)` lanza un `TypeError` accidental al leer `response.user.id`; el `catch` de `LoginContainer` atrapa esa excepción y muestra el fallback genérico `"Ocurrió un error inesperado al iniciar sesión."` dentro de `role="alert"`, haciendo que el test pase con un falso positivo. Igualmente, colapsar todos los mensajes a `"Error"` (`FM4-E`) no rompe ninguna aserción.
   - *Acción requerida (`login.test.tsx` y `ui-catalog.test.tsx`):*
     - Afirmar en `401` que `alert` comunica credenciales incorrectas (y no un error genérico/crash inesperado).
     - Afirmar en `422` que `alert` refleja el mensaje de validación (`error.message` / `"Datos inválidos"`), y en `429`, `502`, `503` y error de red (`HttpResponse.error()`) que el texto de `role="alert"` corresponde específicamente a demasiados intentos, indisponibilidad/timeout del servicio o fallo de conexión (nunca el fallback de excepción no tipada).

2. **Ausencia de test para `"Cerrar sesión"` dentro del flujo de onboarding (`FM3-C`):**
   - *Causa raíz:* `specs/auth-onboarding-ui/spec.md` (L85–86 y L113–116) exige explícitamente que el usuario autenticado dentro del flujo de onboarding disponga de cierre de sesión explícito (`"Cerrar sesión"` → `POST /api/v1/auth/logout`, limpieza de `localStorage` y caché, y redirección a `/login`). Ningún test en `onboarding.test.tsx` ni `session.test.tsx` ejercita ese botón dentro del diálogo de onboarding (`allowLogout` en `OnboardingContainer`).
   - *Acción requerida (`onboarding.test.tsx` o `session.test.tsx`):*
     - Agregar un caso en `requires_onboarding: true` sobre `/` que active el botón `"Cerrar sesión"` dentro de `role="dialog"`, verificando llamada a `POST /api/v1/auth/logout`, limpieza de `localStorage` y navegación a `/login`.

3. **Ausencia de cobertura de errores HTTP `422` (y errores de red/`5xx`) en `POST /api/v1/auth/onboarding` (`FM5-E`):**
   - *Causa raíz:* `frontend/src/test/auth/onboarding.test.tsx` cubre `201`, `409` y `401`, pero no prueba respuestas `422` (`VALIDATION_ERROR`) ni fallos de red en `/api/v1/auth/onboarding`, permitiendo que `onboardingRequest` enmascare un `422` como creación exitosa de comercio sin ser detectado.
   - *Acción requerida (`onboarding.test.tsx`):*
     - Agregar caso para `POST /api/v1/auth/onboarding` devolviendo HTTP `422` (`ErrorResponse`), verificando que el diálogo permanece abierto, no se guarda negocio en `localStorage`, no redirige a `/` y muestra el mensaje de error en `role="alert"` dentro del modal. (Opcionalmente verificar también fallo de red en onboarding).

4. **Ausencia de prueba para fallo de red en `GET /api/v1/auth/me` durante bootstrap (`FM2-D`):**
   - *Causa raíz:* `design.md` (§Persistencia local y seguridad, L190) especifica que si `GET /api/v1/auth/me` falla por error de red y existe `rvm.auth.context` previo con `requires_onboarding: false`, el contexto público permanece disponible para renderizado UI offline-aware (implementado en `AuthContext.tsx` L61–66). Ningún test en `session.test.tsx` mockea `GET /api/v1/auth/me` con `HttpResponse.error()` y caché previa.
   - *Acción requerida (`session.test.tsx`):*
     - Agregar test con `rvm.auth.context` válido (`requires_onboarding: false`) en `localStorage` y `GET /api/v1/auth/me` respondiendo `HttpResponse.error()`, comprobando que conserva el contexto público sin redirigir erróneamente a `/login` (mientras que un `401` sí lo limpia).
