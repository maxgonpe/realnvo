import sqlite3
import psycopg2
from psycopg2 import sql

POSTGRESQL_CONFIG = {
    'NAME': 'extintores',
    'USER': 'max',
    'PASSWORD': 'celsa1961',
    'HOST': 'localhost',
    'PORT': 5432
}

SQLITE_PATH = 'db.sqlite3'

def convertir_booleans(row, columnas, tipos_sqlite):
    nueva_fila = []
    for i, valor in enumerate(row):
        tipo = tipos_sqlite[i].lower()
        if tipo in ("boolean", "bool"):
            nueva_fila.append(True if valor in (1, "1") else False if valor in (0, "0") else None)
        else:
            nueva_fila.append(valor)
    return tuple(nueva_fila)

def copiar_tabla(nombre_tabla, sqlite_cursor, pg_cursor, pg_conn):
    try:
        sqlite_cursor.execute(f"PRAGMA table_info({nombre_tabla})")
        info_columnas = sqlite_cursor.fetchall()
        tipos_sqlite = [col[2] for col in info_columnas]
        columnas = [col[1] for col in info_columnas]

        sqlite_cursor.execute(f"SELECT * FROM {nombre_tabla}")
        rows = sqlite_cursor.fetchall()

        if not rows:
            print(f"⚠️ Tabla {nombre_tabla} vacía, se omite.")
            return True

        pg_cursor.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(nombre_tabla)))
        print(f"✔️ Datos anteriores de {nombre_tabla} eliminados.")

        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(columnas))
        insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(nombre_tabla),
            sql.SQL(', ').join(map(sql.Identifier, columnas)),
            placeholders
        )

        values = [convertir_booleans(row, columnas, tipos_sqlite) for row in rows]
        pg_cursor.executemany(insert_query.as_string(pg_conn), values)
        pg_conn.commit()
        print(f"✅ {len(values)} registros insertados en {nombre_tabla}.")
        return True

    except Exception as e:
        print(f"❌ Error insertando en {nombre_tabla}: {e}")
        pg_conn.rollback()
        return False

def copiar_todas_las_tablas():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    todas = [row['name'] for row in sqlite_cursor.fetchall()]

    # Orden lógico según dependencias (personaliza si agregas más)
    orden = [
        'auth_user',
        'auth_group',
        'auth_permission',
        'auth_group_permissions',
        'auth_user_groups',
        'auth_user_user_permissions',
        'django_content_type',
        'django_migrations',
        'django_session',
        'django_admin_log',
        'extintores_categoriaproducto',
        'extintores_producto',
        'extintores_cliente',
        'extintores_categoriaproducto_componentes_relacionados',
        'extintores_intervencion',
        'extintores_odt',
        'extintores_technicianprofile',
        'extintores_itemodt',
        'extintores_detalleodt',
        'extintores_detalleintervencion',
        'extintores_compatibilidadproducto',
        'extintores_bitacora',
        'extintores_imagenintervencion',
        'django_summernote_attachment',
        'extintores_factorajustecliente',
    ]

    restantes = [t for t in todas if t not in orden]
    tablas = orden + restantes

    print(f"Tablas ordenadas: {tablas}")

    pg_conn = psycopg2.connect(
        dbname=POSTGRESQL_CONFIG['NAME'],
        user=POSTGRESQL_CONFIG['USER'],
        password=POSTGRESQL_CONFIG['PASSWORD'],
        host=POSTGRESQL_CONFIG['HOST'],
        port=POSTGRESQL_CONFIG['PORT']
    )
    pg_cursor = pg_conn.cursor()

    fallidas = []

    # Primera pasada
    for tabla in tablas:
        print(f"\n📋 Copiando tabla: {tabla}")
        ok = copiar_tabla(tabla, sqlite_cursor, pg_cursor, pg_conn)
        if not ok:
            fallidas.append(tabla)

    # Segunda pasada: intenta de nuevo las fallidas
    if fallidas:
        print("\n🔁 Reintentando las tablas fallidas...")
        pendientes = []
        for tabla in fallidas:
            print(f"\n📋 Reintentando tabla: {tabla}")
            ok = copiar_tabla(tabla, sqlite_cursor, pg_cursor, pg_conn)
            if not ok:
                pendientes.append(tabla)

        fallidas = pendientes

    pg_cursor.close()
    pg_conn.close()
    sqlite_conn.close()

    print("\n🚀 Copia finalizada.")
    if fallidas:
        print("\n⚠️ Tablas que aún fallaron:")
        for t in fallidas:
            print(f" - {t}")
    else:
        print("✅ Todas las tablas copiadas correctamente.")

if __name__ == "__main__":
    copiar_todas_las_tablas()


#ejecutar este comando despues de correr el script:
# python3 manage.py sqlsequencereset extintores auth admin | python manage.py dbshell
