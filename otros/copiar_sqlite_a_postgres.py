import sqlite3
import psycopg2
from psycopg2 import sql

# Configuración de PostgreSQL
POSTGRESQL_CONFIG = {
    'NAME': 'extintores',
    'USER': 'maxgonpe',
    'PASSWORD': '19331941',
    'HOST': 'localhost',
    'PORT': 5432
}

SQLITE_PATH = 'db.sqlite3'

def convertir_booleans(row, columnas, tipos_sqlite):
    nueva_fila = []
    for i, valor in enumerate(row):
        tipo = tipos_sqlite[i].lower()
        if tipo == "boolean" or tipo == "bool":
            nueva_fila.append(True if valor in (1, "1") else False if valor in (0, "0") else None)
        else:
            nueva_fila.append(valor)
    return tuple(nueva_fila)

def copiar_todas_las_tablas():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tablas = [row['name'] for row in sqlite_cursor.fetchall()]
    print(f"Tablas encontradas en SQLite: {tablas}")

    pg_conn = psycopg2.connect(
        dbname=POSTGRESQL_CONFIG['NAME'],
        user=POSTGRESQL_CONFIG['USER'],
        password=POSTGRESQL_CONFIG['PASSWORD'],
        host=POSTGRESQL_CONFIG['HOST'],
        port=POSTGRESQL_CONFIG['PORT']
    )
    pg_cursor = pg_conn.cursor()

    # Desactiva restricciones de claves foráneas temporalmente
    pg_cursor.execute("SET session_replication_role = 'replica';")

    tablas_fallidas = []

    for tabla in tablas:
        print(f"\n📋 Copiando tabla: {tabla}")

        try:
            sqlite_cursor.execute(f"PRAGMA table_info({tabla})")
            info_columnas = sqlite_cursor.fetchall()
            tipos_sqlite = [col[2] for col in info_columnas]
            columnas = [col[1] for col in info_columnas]

            sqlite_cursor.execute(f"SELECT * FROM {tabla}")
            rows = sqlite_cursor.fetchall()

            if not rows:
                print(f"⚠️ Tabla {tabla} vacía, se omite.")
                continue

            # Borrar datos anteriores
            pg_cursor.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(tabla)))
            print(f"✔️ Datos anteriores de {tabla} eliminados.")

            placeholders = sql.SQL(', ').join(sql.Placeholder() * len(columnas))
            insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(tabla),
                sql.SQL(', ').join(map(sql.Identifier, columnas)),
                placeholders
            )

            values = [convertir_booleans(row, columnas, tipos_sqlite) for row in rows]

            pg_cursor.executemany(insert_query.as_string(pg_conn), values)
            pg_conn.commit()
            print(f"✅ {len(values)} registros insertados en {tabla}.")

        except Exception as e:
            print(f"❌ Error insertando en {tabla}: {e}")
            pg_conn.rollback()
            tablas_fallidas.append(tabla)

    # Restaurar las claves foráneas
    pg_cursor.execute("SET session_replication_role = 'origin';")
    pg_conn.commit()

    pg_cursor.close()
    pg_conn.close()
    sqlite_conn.close()

    print("\n🚀 Copia finalizada.")

    if tablas_fallidas:
        print("\n⚠️ Tablas con error:")
        for t in tablas_fallidas:
            print(f" - {t}")

if __name__ == "__main__":
    copiar_todas_las_tablas()



'''
import sqlite3
import psycopg2
from psycopg2 import sql

# Configuración de PostgreSQL
POSTGRESQL_CONFIG = {
    'NAME': 'extintores',
    'USER': 'maxgonpe',
    'PASSWORD': '19331941',
    'HOST': 'localhost',
    'PORT': 5432
}

# Ruta a tu archivo SQLite
SQLITE_PATH = 'db.sqlite3'

def copiar_todas_las_tablas():
    # Conexión a SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Obtener todas las tablas (excluye las internas de SQLite)
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tablas = [row['name'] for row in sqlite_cursor.fetchall()]
    print(f"Tablas encontradas en SQLite: {tablas}")

    # Conexión a PostgreSQL
    pg_conn = psycopg2.connect(
        dbname=POSTGRESQL_CONFIG['NAME'],
        user=POSTGRESQL_CONFIG['USER'],
        password=POSTGRESQL_CONFIG['PASSWORD'],
        host=POSTGRESQL_CONFIG['HOST'],
        port=POSTGRESQL_CONFIG['PORT']
    )
    pg_cursor = pg_conn.cursor()

    for tabla in tablas:
        print(f"\n📋 Copiando tabla: {tabla}")

        # Leer datos de SQLite
        sqlite_cursor.execute(f"SELECT * FROM {tabla}")
        rows = sqlite_cursor.fetchall()
        columnas = [desc[0] for desc in sqlite_cursor.description]

        if not rows:
            print(f"⚠️ Tabla {tabla} vacía, se omite.")
            continue

        # Borrar datos anteriores en PostgreSQL
        try:
            pg_cursor.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(tabla)))
            print(f"✔️ Datos anteriores de {tabla} eliminados.")
        except Exception as e:
            print(f"❌ Error al eliminar datos de {tabla}: {e}")
            pg_conn.rollback()
            continue

        # Insertar datos
        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(columnas))
        insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(tabla),
            sql.SQL(', ').join(map(sql.Identifier, columnas)),
            placeholders
        )

        values = [tuple(row[col] for col in columnas) for row in rows]

        try:
            pg_cursor.executemany(insert_query.as_string(pg_conn), values)
            pg_conn.commit()
            print(f"✅ {len(values)} registros insertados en {tabla}.")
        except Exception as e:
            print(f"❌ Error insertando en {tabla}: {e}")
            pg_conn.rollback()

    # Cerrar conexiones
    sqlite_conn.close()
    pg_cursor.close()
    pg_conn.close()
    print("\n🚀 Copia finalizada.")

if __name__ == "__main__":
    copiar_todas_las_tablas()
'''
