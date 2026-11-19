-- Migracion 005 - Permisos del rol de la aplicacion (pos_app) sobre el schema pos
--
-- pos_app es el usuario con el que la app sincroniza (no es superusuario y no ve `public`).
-- Una tabla nueva queda SIN politica RLS (y por tanto inaccesible para pos_app) hasta que se
-- vuelve a aplicar esta funcion; olvidarlo rompe la sincronizacion en silencio. Por eso:
--   * `pos.aplicar_permisos_pos_app()` es idempotente y se llama al final de cada migracion
--     que crea tablas (tests/unitarias/test_migraciones.py lo exige);
--   * ALTER DEFAULT PRIVILEGES cubre los GRANT de tablas futuras creadas por quien migra.
-- Ejecutar con: SET search_path TO pos;  (o dentro de una transaccion con SET LOCAL).

CREATE OR REPLACE FUNCTION pos.aplicar_permisos_pos_app() RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    r record;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pos_app') THEN
        RAISE NOTICE 'El rol pos_app no existe: no se aplican permisos (crearlo primero).';
        RETURN;
    END IF;
    GRANT USAGE ON SCHEMA pos TO pos_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pos TO pos_app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA pos TO pos_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA pos
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pos_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA pos GRANT USAGE, SELECT ON SEQUENCES TO pos_app;
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'pos' LOOP
        EXECUTE format('ALTER TABLE pos.%I ENABLE ROW LEVEL SECURITY', r.tablename);
        EXECUTE format('DROP POLICY IF EXISTS pos_app_todo ON pos.%I', r.tablename);
        EXECUTE format(
            'CREATE POLICY pos_app_todo ON pos.%I FOR ALL TO pos_app USING (true) WITH CHECK (true)',
            r.tablename
        );
    END LOOP;
END;
$$;

SELECT pos.aplicar_permisos_pos_app();
