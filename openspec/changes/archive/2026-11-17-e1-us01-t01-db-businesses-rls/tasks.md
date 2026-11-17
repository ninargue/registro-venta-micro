## 1. Tests DB-TDD en ROJO

- [x] 1.1 Crear archivo de pruebas de esquema para `businesses` y `business_users` (validación de nulabilidad, tipos y constraints) en `backend/tests/integration/test_db_businesses.py`
- [x] 1.2 Crear pruebas de aislamiento RLS verificando que `app.current_business_id` aísla los registros entre negocios
- [x] 1.3 Ejecutar tests y confirmar el estado en ROJO por ausencia de las tablas

## 2. Modelos SQLAlchemy y Migración Alembic

- [x] 2.1 Crear modelos ORM `Business` y `BusinessUser` con metadata y constraints en `backend/app/modules/auth/models.py`
- [x] 2.2 Crear script de migración Alembic en `backend/migrations/versions/` para la creación de tablas `businesses` y `business_users`

## 3. Políticas RLS y Aislamiento Multi-Tenant

- [x] 3.1 Agregar directivas `ENABLE ROW LEVEL SECURITY` y `FORCE ROW LEVEL SECURITY` en la migración de Alembic
- [x] 3.2 Configurar políticas RLS para operaciones basadas en `current_setting('app.current_business_id', true)`
- [x] 3.3 Implementar lógica reversible completa en la función `downgrade()` de la migración

## 4. Verificación en VERDE y Roundtrip

- [x] 4.1 Aplicar migración con `uv run alembic upgrade head` en la base de datos local
- [x] 4.2 Ejecutar suite de pruebas DB-TDD y verificar transición a VERDE
- [x] 4.3 Validar reversibilidad con `alembic downgrade -1` y re-aplicar `alembic upgrade head`
