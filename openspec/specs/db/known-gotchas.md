# Known Gotchas — db

Reglas breves promovidas tras fallos reales del repositorio. Leer solo esta capa en `opsx:explore`.

- En Supabase PG17 postgres tiene usesuper=false; al crear roles como app_api en migraciones incluir GRANT <rol> TO CURRENT_USER para permitir SET LOCAL ROLE.
