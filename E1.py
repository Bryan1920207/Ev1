import datetime
import sys
from tabulate import tabulate
import sqlite3
from sqlite3 import Error
import os
import csv
import json

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side
except Exception:
    openpyxl = None

clientes = []
salas = []
reservas = []

next_cliente_id = 1
next_sala_id = 1
next_folio = 1001

DB_FILE = "Evidencia.db"
FORMATO_FECHA_INPUT = "%m-%d-%Y"   
FORMATO_FECHA_ISO = "%Y-%m-%d"    

def analizar_fecha_o_none(texto_fecha):
    if texto_fecha == "":
        return "VACIO"
    if any(c.isalpha() for c in texto_fecha):
        return "LETRAS"   
    if any(c in ",./\\" for c in texto_fecha) and "-" not in texto_fecha:
        return "SEPARADOR"
    try:
        return datetime.datetime.strptime(texto_fecha, FORMATO_FECHA_INPUT).date()
    except ValueError:
        return None

def es_nombre_valido(texto_nombre):
    return bool(texto_nombre) and texto_nombre.replace(" ", "").isalpha()

def es_nombre_sala_valido(texto_nombre_sala):
    return bool(texto_nombre_sala) and all(car.isalpha() or car.isspace() for car in texto_nombre_sala)

def es_entero_positivo(texto_numero):
    return texto_numero.isdigit() and int(texto_numero) > 0

def asegurar_tablas():
    crear = False
    if not os.path.exists(DB_FILE):
        crear = True
    else:
        try:
            conexion = sqlite3.connect(DB_FILE)
            cursor = conexion.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clientes';")
            if not cursor.fetchone():
                crear = True
            cursor.close()
            conexion.close()
        except Exception as err:
            print(f"Error comprobando esquema de BD: {err}")
            crear = True
    if crear:
        ddl = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS clientes (
  cliente_id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  apellidos TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS salas (
  sala_id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL UNIQUE,
  cupo INTEGER NOT NULL CHECK (cupo > 0)
);
CREATE TABLE IF NOT EXISTS reservas (
  folio INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id INTEGER NOT NULL,
  sala_id INTEGER NOT NULL,
  fecha_normalizada DATE NOT NULL,
  turno TEXT NOT NULL CHECK (turno IN ('Matutino','Vespertino','Nocturno')),
  evento TEXT NOT NULL,
  FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id),
  FOREIGN KEY (sala_id) REFERENCES salas(sala_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_reserva_sala_fecha_turno
  ON reservas (sala_id, fecha_normalizada, turno);
CREATE INDEX IF NOT EXISTS ix_reserva_fecha ON reservas (fecha_normalizada);
CREATE INDEX IF NOT EXISTS ix_reserva_cliente ON reservas (cliente_id);
"""
        try:
            with sqlite3.connect(DB_FILE) as conexion:
                conexion.executescript(ddl)
        except Error as e:
            print("Error al crear tablas en la base de datos:", e)
            sys.exit(1)

def cargar_estado_desde_bd():
    global clientes, salas, reservas, next_cliente_id, next_sala_id, next_folio
    asegurar_tablas()
    try:
        with sqlite3.connect(DB_FILE) as conexion:
            conexion.row_factory = sqlite3.Row
            cursor = conexion.cursor()
            cursor.execute("SELECT cliente_id AS id, nombre, apellidos FROM clientes ORDER BY apellidos, nombre")
            filas_clientes = cursor.fetchall()
            cursor.execute("SELECT sala_id AS id, nombre, cupo FROM salas ORDER BY nombre")
            filas_salas = cursor.fetchall()
  
            try:
                cursor.execute("SELECT folio, cliente_id, sala_id, fecha_normalizada, turno, evento FROM reservas ORDER BY folio")
                filas_reservas = cursor.fetchall()
            except Exception:
                cursor.execute("SELECT folio, cliente_id, sala_id, turno, evento FROM reservas ORDER BY folio")
                filas_reservas = cursor.fetchall()
            cursor.close()
        clientes = [{"id": r["id"], "nombre": r["nombre"], "apellidos": r["apellidos"]} for r in filas_clientes]
        salas = [{"id": r["id"], "nombre": r["nombre"], "cupo": r["cupo"]} for r in filas_salas]
        reservas = []
        for r in filas_reservas:
            fecha_dt = None
            if "fecha_normalizada" in r.keys():
                fecha_texto = r["fecha_normalizada"]
                if fecha_texto:
                    try:
                        fecha_dt = datetime.datetime.strptime(fecha_texto, FORMATO_FECHA_ISO).date()
                    except Exception:
                        try:
                            fecha_dt = datetime.datetime.strptime(fecha_texto, FORMATO_FECHA_INPUT).date()
                        except Exception:
                            fecha_dt = None
            elif "fecha" in r.keys():
                fecha_texto = r["fecha"]
                if fecha_texto:
                    try:
                        fecha_dt = datetime.datetime.strptime(fecha_texto, FORMATO_FECHA_ISO).date()
                    except Exception:
                        try:
                            fecha_dt = datetime.datetime.strptime(fecha_texto, FORMATO_FECHA_INPUT).date()
                        except Exception:
                            fecha_dt = None
            if fecha_dt is None:
                print(f"Advertencia: formato de fecha inválido en BD para folio {r.get('folio')}, registro omitido.")
                continue
            reservas.append({
                "folio": r["folio"],
                "cliente_id": r["cliente_id"],
                "sala_id": r["sala_id"],
                "fecha": fecha_dt,
                "turno": r["turno"],
                "evento": r["evento"]
            })
        try:
            with sqlite3.connect(DB_FILE) as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT MAX(cliente_id) FROM clientes")
                max_cliente = cursor.fetchone()
                if max_cliente and max_cliente[0]:
                    next_cliente_id = max_cliente[0] + 1
                cursor.execute("SELECT MAX(sala_id) FROM salas")
                max_sala = cursor.fetchone()
                if max_sala and max_sala[0]:
                    next_sala_id = max_sala[0] + 1
                cursor.execute("SELECT MAX(folio) FROM reservas")
                max_folio = cursor.fetchone()
                if max_folio and max_folio[0]:
                    next_folio = max_folio[0] + 1
                cursor.close()
        except Exception as err:
            print(f"Advertencia sincronizando contadores desde BD: {err}")
        return True
    except Exception as err:
        print(f"No se pudo cargar estado desde BD: {err}")
        return False

def insertar_cliente_bd(nombre_cliente, apellidos_cliente):
    try:
        asegurar_tablas()
        with sqlite3.connect(DB_FILE) as conexion:
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO clientes(nombre,apellidos) VALUES(?,?)", (nombre_cliente, apellidos_cliente))
            conexion.commit()
            ultimo_id = cursor.lastrowid
            cursor.close()
            return ultimo_id
    except sqlite3.IntegrityError as err:
        print(f"Cliente no insertado en BD (error de integridad): {err}")
        return None
    except Exception as err:
        print(f"Error al insertar cliente en BD: {err}")
        return None

def insertar_sala_bd(nombre_sala, cupo_sala):
    try:
        asegurar_tablas()
        with sqlite3.connect(DB_FILE) as conexion:
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO salas(nombre,cupo) VALUES(?,?)", (nombre_sala, cupo_sala))
            conexion.commit()
            ultimo_id = cursor.lastrowid
            cursor.close()
            return ultimo_id
    except sqlite3.IntegrityError as err:
        print(f"Sala no insertada en BD (error de integridad): {err}")
        return None
    except Exception as err:
        print(f"Error al insertar sala en BD: {err}")
        return None

def insertar_reserva_bd(cliente_id_param, sala_id_param, fecha_normalizada_texto, turno_param, evento_param):
    try:
        asegurar_tablas()
        with sqlite3.connect(DB_FILE) as conexion:
            conexion.row_factory = sqlite3.Row
            cursor = conexion.cursor()

            cursor.execute("PRAGMA table_info(reservas);")
            filas_info = cursor.fetchall()
            columnas = [fila["name"] if isinstance(fila, sqlite3.Row) or isinstance(fila, dict) else fila[1] for fila in filas_info]
            if "fecha_normalizada" in columnas:
                col_fecha = "fecha_normalizada"
            elif "fecha" in columnas:
                col_fecha = "fecha"
            else:
                try:
                    cursor.execute("ALTER TABLE reservas ADD COLUMN fecha_normalizada DATE")
                    conexion.commit()
                    col_fecha = "fecha_normalizada"
                except Exception:
                    col_fecha = "fecha_normalizada"

            consulta_conflicto = f"SELECT 1 FROM reservas WHERE sala_id=? AND {col_fecha}=? AND turno=?"
            cursor.execute(consulta_conflicto, (sala_id_param, fecha_normalizada_texto, turno_param))
            if cursor.fetchone():
                cursor.close()
                return None

            consulta_insert = f"INSERT INTO reservas(cliente_id,sala_id,{col_fecha},turno,evento) VALUES(?,?,?,?,?)"
            try:
                cursor.execute(consulta_insert, (cliente_id_param, sala_id_param, fecha_normalizada_texto, turno_param, evento_param))
                conexion.commit()
                folio_generado = cursor.lastrowid
                cursor.close()
                return folio_generado
            except sqlite3.IntegrityError as ie:
                if "fecha" in columnas and "fecha_normalizada" in columnas:
                    try:
                        consulta_insert2 = "INSERT INTO reservas(cliente_id,sala_id,fecha,fecha_normalizada,turno,evento) VALUES(?,?,?,?,?,?)"
                        cursor.execute(consulta_insert2, (cliente_id_param, sala_id_param, fecha_normalizada_texto, fecha_normalizada_texto, turno_param, evento_param))
                        conexion.commit()
                        folio_generado = cursor.lastrowid
                        cursor.close()
                        return folio_generado
                    except Exception:
                        pass

                print(f"Reserva no insertada en BD (error de integridad): {ie}")
                cursor.close()
                return None
    except sqlite3.IntegrityError as err:
        print(f"Reserva no insertada en BD (error de integridad): {err}")
        return None
    except Exception as err:
        print(f"Error al insertar reserva en BD: {err}")
        return None

def generar_reporte_por_fecha_lista(fecha_consulta):
    filas_reporte = []
    for registro_reserva in reservas:
        if registro_reserva["fecha"] == fecha_consulta:
            cliente_encontrado = None
            for registro_cliente in clientes:
                if registro_cliente["id"] == registro_reserva["cliente_id"]:
                    cliente_encontrado = registro_cliente
                    break
            sala_encontrada = None
            for registro_sala in salas:
                if registro_sala["id"] == registro_reserva["sala_id"]:
                    sala_encontrada = registro_sala
                    break
            if cliente_encontrado and sala_encontrada:
                filas_reporte.append([
                    registro_reserva["folio"],
                    registro_reserva["fecha"].strftime(FORMATO_FECHA_INPUT),
                    f"{cliente_encontrado['apellidos']}, {cliente_encontrado['nombre']}",
                    sala_encontrada["nombre"],
                    sala_encontrada["cupo"],
                    registro_reserva["turno"],
                    registro_reserva["evento"]
                ])
    return filas_reporte

def imprimir_reporte_tabular_por_fecha(fecha_consulta):
    filas = generar_reporte_por_fecha_lista(fecha_consulta)
    if not filas:
        print("No hay reservaciones para la fecha indicada.")
        return False
    encabezado = f"REPORTE DE RESERVACIONES PARA EL {fecha_consulta.strftime(FORMATO_FECHA_INPUT)}"
    print("\n" + "=" * 60)
    print(encabezado.center(60))
    print("=" * 60)
    print(tabulate(filas, headers=["FOLIO", "FECHA", "CLIENTE", "SALA", "CUPO", "TURNO", "EVENTO"], tablefmt="grid"))
    print("FIN DEL REPORTE\n")
    return True

def exportar_reporte_json(fecha_consulta, filas_export):
    if not filas_export:
        print("No hay datos para exportar en esa fecha.")
        return
    nombre_archivo = f"reporte_{fecha_consulta.strftime('%Y%m%d')}.json"
    datos_json = []
    for fila in filas_export:
        datos_json.append({
            "folio": fila[0],
            "fecha": fila[1],
            "cliente": fila[2],
            "sala": fila[3],
            "cupo": fila[4],
            "turno": fila[5],
            "evento": fila[6]
        })
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as archivo_salida:
            json.dump(datos_json, archivo_salida, ensure_ascii=False, indent=2)
        print(f"Reporte JSON guardado como {nombre_archivo}.")
    except Exception as err:
        print(f"Error al exportar JSON: {err}")

def exportar_reporte_csv(fecha_consulta, filas_export):
    if not filas_export:
        print("No hay datos para exportar en esa fecha.")
        return
    nombre_archivo = f"reporte_{fecha_consulta.strftime('%Y%m%d')}.csv"
    try:
        with open(nombre_archivo, "w", newline='', encoding="utf-8") as archivo_csv:
            escritor = csv.writer(archivo_csv)
            escritor.writerow(["FOLIO","FECHA","CLIENTE","SALA","CUPO","TURNO","EVENTO"])
            for fila in filas_export:
                escritor.writerow(fila)
        print(f"Reporte CSV guardado como {nombre_archivo}.")
    except Exception as err:
        print(f"Error al exportar CSV: {err}")

def exportar_reporte_excel(fecha_consulta, filas_export):
    if openpyxl is None:
        print("openpyxl no está instalado. Instale openpyxl para exportar a Excel.")
        return
    if not filas_export:
        print("No hay datos para exportar en esa fecha.")
        return
    nombre_archivo = f"reporte_{fecha_consulta.strftime('%Y%m%d')}.xlsx"
    try:
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.title = "Reservas"
        hoja.merge_cells('A1:G1')
        hoja['A1'] = f"REPORTE RESERVACIONES {fecha_consulta.strftime(FORMATO_FECHA_INPUT)}"
        hoja['A1'].font = Font(bold=True)
        encabezados = ["FOLIO","FECHA","CLIENTE","SALA","CUPO","TURNO","EVENTO"]
        for indice_columna, titulo_columna in enumerate(encabezados, start=1):
            celda = hoja.cell(row=2, column=indice_columna, value=titulo_columna)
            celda.font = Font(bold=True)
            celda.alignment = Alignment(horizontal="center")
            celda.border = Border(bottom=Side(border_style="thick"))
        for indice_fila, fila_datos in enumerate(filas_export, start=3):
            for indice_columna, valor in enumerate(fila_datos, start=1):
                celda = hoja.cell(row=indice_fila, column=indice_columna, value=valor)
                celda.alignment = Alignment(horizontal="center")
        libro.save(nombre_archivo)
        print(f"Reporte Excel guardado como {nombre_archivo}.")
    except Exception as err:
        print(f"Error al exportar Excel: {err}")

inicio_bd_ok = cargar_estado_desde_bd()
if inicio_bd_ok:
    print("=" * 60)
    print("Estado inicial cargado desde Evidencia.db".center(60))
    print("=" * 60)
else:
    print("=" * 60)
    print("No se pudo cargar Evidencia.db; iniciando con estado vacío en memoria".center(60))
    print("=" * 60)

while True:
    print("\n" + "=" * 60)
    print(" ----- MENU PRINCIPAL ----- ".center(60))
    print("=" * 60)
    print("1. Registrar reservación de una sala.")
    print("2. Editar evento.")
    print("3. Consultar reservaciones por fecha.")
    print("4. Registrar un nuevo cliente.")
    print("5. Registrar una sala.")
    print("6. Salir.")
    print("=" * 60)

    try:
        opcion_texto = input("Seleccionar una opción (1-6): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nOperación cancelada por teclado.")
        sys.exit()
    if opcion_texto == "":
        print("Entrada vacía: ingrese un número entre 1 y 6.")
        continue
    if not opcion_texto.isdigit():
        print("Formato inválido: la opción debe ser numérica entre 1 y 6.")
        continue
    opcion = int(opcion_texto)
    if opcion < 1 or opcion > 6:
        print("Opción fuera de rango: seleccione un valor entre 1 y 6.")
        continue

    if opcion == 1:
        print("\n" + "=" * 60)
        print("REGISTRAR RESERVACIÓN".center(60))
        print("=" * 60)
        cancelar = False

        while True:
            try:
                texto_fecha = input("Ingrese fecha de reservación (MM-DD-YYYY) o 'X' para cancelar: ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada de fecha.")
                cancelar = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada de fecha.")
                cancelar = True
                break
            if texto_fecha.upper() == "X":
                print("Operación cancelada por el usuario.")
                cancelar = True
                break
            if texto_fecha == "":
                print("Fecha inválida: el campo 'Fecha' está vacío. Formato esperado: MM-DD-YYYY.")
                continue
            resultado_fecha = analizar_fecha_o_none(texto_fecha)
            if resultado_fecha == "LETRAS":
                print("Fecha inválida: hay letras en la fecha. Use solo dígitos y guiones, por ejemplo 12-31-2025.")
                continue
            if resultado_fecha == "SEPARADOR":
                print("Fecha inválida: separadores incorrectos. Use '-' entre mes, día y año. Ejemplo: MM-DD-YYYY.")
                continue
            if resultado_fecha is None:
                print("Fecha inválida: formato incorrecto. Use MM-DD-YYYY, por ejemplo 12-31-2025.")
                continue
            fecha = resultado_fecha
            if fecha < datetime.date.today() + datetime.timedelta(days=2):
                print("Restricción de antelación: la fecha debe ser al menos dos días posterior a hoy.")
                continue
            if fecha.weekday() == 6:
                lunes_propuesto = fecha + datetime.timedelta(days=1)
                while True:
                    try:
                        respuesta_domingo = input(f"La fecha ingresada es domingo. Se propone {lunes_propuesto.strftime(FORMATO_FECHA_INPUT)}. ¿Aceptar? (S/N) o 'X' para cancelar: ").strip().upper()
                    except EOFError:
                        print("Interrupción por EOF durante confirmación de domingo.")
                        respuesta_domingo = "X"
                    except KeyboardInterrupt:
                        print("Interrupción por teclado durante confirmación de domingo.")
                        respuesta_domingo = "X"
                    if respuesta_domingo == "X":
                        cancelar = True
                        break
                    if respuesta_domingo == "":
                        print("Respuesta vacía: escriba 'S' para aceptar o 'N' para rechazar.")
                        continue
                    if respuesta_domingo not in ("S", "N"):
                        print("Respuesta inválida: escriba 'S' para aceptar o 'N' para rechazar.")
                        continue
                    if respuesta_domingo == "S":
                        fecha = lunes_propuesto
                    break
                if cancelar:
                    break

            print(f"Fecha aceptada: {fecha.strftime(FORMATO_FECHA_INPUT)}")
            break
        if cancelar:
            continue

        while True:
            clientes_bd = []
            try:
                with sqlite3.connect(DB_FILE) as conexion:
                    conexion.row_factory = sqlite3.Row
                    cursor = conexion.cursor()
                    cursor.execute("SELECT cliente_id, apellidos, nombre FROM clientes ORDER BY apellidos, nombre")
                    clientes_bd = cursor.fetchall()
                    cursor.close()
            except Exception as err:
                print(f"Advertencia: fallo al leer lista de clientes desde BD: {err}")
                clientes_bd = []

            if clientes_bd:
                print("\n" + "-" * 60)
                print("Clientes registrados:".center(60))
                print("-" * 60)
                for fila_cliente in clientes_bd:
                    print(f"{fila_cliente['cliente_id']}: {fila_cliente['apellidos']}, {fila_cliente['nombre']}")
                try:
                    sel_cliente_texto = input("Ingrese ID de cliente o 'X' para cancelar: ").strip()
                except EOFError:
                    print("Interrupción por EOF durante selección de cliente.")
                    sel_cliente_texto = "X"
                except KeyboardInterrupt:
                    print("Interrupción por teclado durante selección de cliente.")
                    sel_cliente_texto = "X"
                if sel_cliente_texto.upper() == "X":
                    cancelar = True
                    break
                if sel_cliente_texto == "":
                    print("ID inválido: el campo está vacío.")
                    continue
                if sel_cliente_texto == "0":
                    print("ID inválido: el número debe ser mayor a 0.")
                    continue
                if not sel_cliente_texto.isdigit():
                    print("ID inválido: no se aceptan letras en el ID del cliente.")
                    continue
                cliente_id = int(sel_cliente_texto)
                encontrado = any(fila['cliente_id'] == cliente_id for fila in clientes_bd)
                if not encontrado:
                    print("ID no encontrado en la lista mostrada. Revise e intente de nuevo.")
                    continue
                print(f"Cliente seleccionado: ID {cliente_id}")
                break
            else:
                if not clientes:
                    print("No hay clientes registrados. Use la opción 4 para registrar un cliente o escriba 'X' para cancelar.")
                    try:
                        respuesta = input("Escriba 'X' para cancelar o Enter para volver al menú: ").strip().upper()
                    except EOFError:
                        print("Interrupción por EOF durante aviso de clientes.")
                        respuesta = "X"
                    except KeyboardInterrupt:
                        print("Interrupción por teclado durante aviso de clientes.")
                        respuesta = "X"
                    if respuesta == "X":
                        cancelar = True
                        break
                    else:
                        break
                print("\n" + "-" * 60)
                print("Clientes registrados (memoria):".center(60))
                print("-" * 60)
                for registro_cliente in sorted(clientes, key=lambda x: (x['apellidos'], x['nombre'])):
                    print(f"{registro_cliente['id']}: {registro_cliente['apellidos']}, {registro_cliente['nombre']}")
                try:
                    sel_cliente_texto = input("Ingrese ID de cliente o 'X' para cancelar: ").strip()
                except EOFError:
                    print("Interrupción por EOF durante selección de cliente en memoria.")
                    sel_cliente_texto = "X"
                except KeyboardInterrupt:
                    print("Interrupción por teclado durante selección de cliente en memoria.")
                    sel_cliente_texto = "X"
                if sel_cliente_texto.upper() == "X":
                    cancelar = True
                    break
                if sel_cliente_texto == "":
                    print("ID inválido: el campo está vacío.")
                    continue
                if sel_cliente_texto == "0":
                    print("ID inválido: el número debe ser mayor a 0.")
                    continue
                if not sel_cliente_texto.isdigit():
                    print("ID inválido: no se aceptan letras en el ID del cliente.")
                    continue
                cliente_id = int(sel_cliente_texto)
                encontrado_memoria = any(registro_cliente['id'] == cliente_id for registro_cliente in clientes)
                if not encontrado_memoria:
                    print("ID no encontrado en la lista mostrada. Revise e intente de nuevo.")
                    continue
                print(f"Cliente seleccionado (memoria): ID {cliente_id}")
                break
        if cancelar:
            continue

        fecha_norm_texto = fecha.strftime(FORMATO_FECHA_ISO)
        disponibles = []
        try:
            with sqlite3.connect(DB_FILE) as conexion:
                conexion.row_factory = sqlite3.Row
                cursor = conexion.cursor()
                cursor.execute("SELECT sala_id, nombre, cupo FROM salas ORDER BY nombre")
                filas_salas = cursor.fetchall()
                cursor.close()
            for fila_sala in filas_salas:
                sala_id_tmp = fila_sala['sala_id']
                sala_nombre_tmp = fila_sala['nombre']
                sala_cupo_tmp = fila_sala['cupo']
                for turno_posible in ("Matutino", "Vespertino", "Nocturno"):
                    try:
                        with sqlite3.connect(DB_FILE) as conexion_check:
                            cursor_check = conexion_check.cursor()
                            cursor_check.execute("SELECT 1 FROM reservas WHERE sala_id=? AND fecha_normalizada=? AND turno=?",
                                                 (sala_id_tmp, fecha_norm_texto, turno_posible))
                            ocupado_bd = cursor_check.fetchone() is not None
                            cursor_check.close()
                    except Exception:
                        ocupado_bd = True
                    if not ocupado_bd:
                        disponibles.append((sala_id_tmp, sala_nombre_tmp, sala_cupo_tmp, turno_posible))
        except Exception as err:
            print(f"Advertencia: fallo al leer salas desde BD: {err}")
            if not salas:
                print("No hay salas registradas. Use la opción 5 para registrar salas o escriba 'X' para cancelar.")
                try:
                    resp = input("Escriba 'X' para cancelar o Enter para intentar de nuevo: ").strip().upper()
                except EOFError:
                    print("Interrupción por EOF durante aviso de salas.")
                    resp = "X"
                except KeyboardInterrupt:
                    print("Interrupción por teclado durante aviso de salas.")
                    resp = "X"
                if resp == "X":
                    cancelar = True
                else:
                    pass
            for registro_sala in salas:
                for turno_posible in ("Matutino", "Vespertino", "Nocturno"):
                    ocupado_memoria = False
                    for registro_reserva in reservas:
                        if registro_reserva['sala_id'] == registro_sala['id'] and registro_reserva['fecha'] == fecha and registro_reserva['turno'] == turno_posible:
                            ocupado_memoria = True
                            break
                    if not ocupado_memoria:
                        disponibles.append((registro_sala['id'], registro_sala['nombre'], registro_sala['cupo'], turno_posible))

        if not disponibles:
            print("\n" + "-" * 60)
            print("ATENCIÓN".center(60))
            print("-" * 60)
            print("No existen salas con turnos libres para la fecha indicada.")
            print("Revise la fecha o cree salas con cupo disponible.")
            print("-" * 60 + "\n")
            continue

        print("\n" + "-" * 60)
        print(f"Salas disponibles para {fecha.strftime(FORMATO_FECHA_INPUT)}".center(60))
        print("-" * 60)
        for registro_disponible in disponibles:
            id_sala_disp = registro_disponible[0]
            nombre_sala_disp = registro_disponible[1]
            cupo_sala_disp = registro_disponible[2]
            turno_disp = registro_disponible[3]
            print(f"{id_sala_disp}: {nombre_sala_disp} (cupo {cupo_sala_disp}) - {turno_disp}")

        while True:
            try:
                sel_sala_texto = input("Ingrese ID de sala o 'X' para cancelar: ").strip()
            except EOFError:
                print("Interrupción por EOF durante selección de sala.")
                cancelar = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante selección de sala.")
                cancelar = True
                break
            if sel_sala_texto.upper() == "X":
                cancelar = True
                break
            if sel_sala_texto == "":
                print("ID de sala inválido: campo vacío.")
                continue
            if sel_sala_texto == "0":
                print("ID inválido: el número debe ser mayor a 0.")
                continue
            if not sel_sala_texto.isdigit():
                print("ID de sala inválido: no se aceptan letras en el ID.")
                continue
            sala_id = int(sel_sala_texto)

            existe_en_lista = any(registro_disponible[0] == sala_id for registro_disponible in disponibles)
            existe_en_bd = False
            try:
                with sqlite3.connect(DB_FILE) as conexion:
                    cursor = conexion.cursor()
                    cursor.execute("SELECT sala_id FROM salas WHERE sala_id=?", (sala_id,))
                    existe_en_bd = cursor.fetchone() is not None
                    cursor.close()
            except Exception:
                existe_en_bd = True
            if existe_en_lista:
                break
            print("\n" + "-" * 60)
            if not existe_en_bd:
                print("ERROR: El identificador de sala ingresado no corresponde a ninguna sala registrada.")
                print("Verifique el ID en la lista mostrada y vuelva a intentar.")
            else:
                print("ERROR: Sala encontrada pero sin turnos libres para la fecha indicada.")
                print("Significado: la sala tiene todas sus franjas horarias ocupadas en la fecha seleccionada.")
            print("-" * 60 + "\n")
            continue

        if cancelar:
            continue

        lista_turnos_disponibles = []
        for registro_disponible in disponibles:
            if registro_disponible[0] == sala_id:
                lista_turnos_disponibles.append(registro_disponible[3])

        print("\nSeleccione el turno disponible para la sala indicada:")
        for indice, descripcion_turno in enumerate(("Matutino", "Vespertino", "Nocturno"), start=1):
            disponible_texto = "DISPONIBLE" if descripcion_turno in lista_turnos_disponibles else "OCUPADO"
            print(f"{indice}. {descripcion_turno} - {disponible_texto}")
        print("X. Cancelar")
        while True:
            try:
                sel_turno_texto = input("Elija el número de turno (1-3) o 'X': ").strip().upper()
            except EOFError:
                print("Interrupción por EOF durante selección de turno.")
                cancelar = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante selección de turno.")
                cancelar = True
                break
            if sel_turno_texto == "X":
                cancelar = True
                break
            if sel_turno_texto == "":
                print("Selección inválida: campo vacío.")
                continue
            if not sel_turno_texto.isdigit():
                print("Selección inválida: no se aceptan letras para seleccionar turno.")
                continue
            num_turno = int(sel_turno_texto)
            if num_turno not in (1, 2, 3):
                print("Selección fuera de rango: elija 1, 2 o 3.")
                continue
            turno_seleccionado = {1: "Matutino", 2: "Vespertino", 3: "Nocturno"}[num_turno]
            if turno_seleccionado not in lista_turnos_disponibles:
                print("Turno no disponible para la sala seleccionada; elija otro.")
                continue
            ocupado_final_memoria = any(registro_reserva['sala_id'] == sala_id and registro_reserva['fecha'] == fecha and registro_reserva['turno'] == turno_seleccionado for registro_reserva in reservas)
            if ocupado_final_memoria:
                print("Turno ahora ocupado (verificación final). Elija otro turno o sala.")
                continue
            break
        if cancelar:
            continue

        while True:
            try:
                nombre_evento_texto = input("Nombre del evento o 'X' para cancelar: ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada del nombre del evento.")
                cancelar = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada del nombre del evento.")
                cancelar = True
                break
            if nombre_evento_texto.upper() == "X":
                cancelar = True
                break
            if nombre_evento_texto == "":
                print("Nombre inválido: el campo 'Nombre del evento' está vacío.")
                continue
            if nombre_evento_texto.strip() == "":
                print("Nombre inválido: no se aceptan solo espacios en blanco para el nombre del evento.")
                continue
            break
        if cancelar:
            continue

        fecha_norm_texto = fecha.strftime(FORMATO_FECHA_ISO)
        folio_generado = insertar_reserva_bd(cliente_id, sala_id, fecha_norm_texto, turno_seleccionado, nombre_evento_texto)
        if folio_generado:
            cargar_estado_desde_bd()
            print("\n" + "=" * 60)
            print(f"Reservación registrada con folio {folio_generado}.")
            print("=" * 60)
            continue

        siguiente_folio = next_folio
        try:
            with sqlite3.connect(DB_FILE) as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT MAX(folio) FROM reservas")
                max_folio_row = cursor.fetchone()
                cursor.close()
                if max_folio_row and max_folio_row[0] and (max_folio_row[0] + 1) > siguiente_folio:
                    siguiente_folio = max_folio_row[0] + 1
        except Exception as err:
            print(f"Advertencia al determinar siguiente folio desde BD: {err}")
        nueva_reserva = {
            "folio": siguiente_folio,
            "cliente_id": cliente_id,
            "sala_id": sala_id,
            "fecha": fecha,
            "turno": turno_seleccionado,
            "evento": nombre_evento_texto
        }
        reservas.append(nueva_reserva)
        try:
            with sqlite3.connect(DB_FILE) as conexion:
                cursor = conexion.cursor()
                cursor.execute("INSERT OR IGNORE INTO reservas(folio,cliente_id,sala_id,fecha_normalizada,turno,evento) VALUES(?,?,?,?,?,?)",
                               (siguiente_folio, cliente_id, sala_id, fecha_norm_texto, turno_seleccionado, nombre_evento_texto))
                conexion.commit()
                cursor.close()
        except Exception as err:
            print(f"Advertencia al intentar persistir reserva con folio explícito: {err}")
        print("\n" + "=" * 60)
        print(f"Reservación registrada en memoria con folio {siguiente_folio}.")
        print("=" * 60)
        next_folio = siguiente_folio + 1

    elif opcion == 2:
        print("\n" + "=" * 60)
        print("EDITAR NOMBRE DE UN EVENTO".center(60))
        print("=" * 60)
        cancelar_edicion = False

        while True:
            try:
                texto_ini = input("Fecha inicial (MM-DD-YYYY) o 'X' para cancelar: ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada de fecha inicial.")
                cancelar_edicion = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada de fecha inicial.")
                cancelar_edicion = True
                break
            if texto_ini.upper() == "X":
                cancelar_edicion = True
                break
            if texto_ini == "":
                print("Fecha inicial inválida: campo vacío.")
                continue
            res_ini = analizar_fecha_o_none(texto_ini)
            if res_ini == "LETRAS":
                print("Fecha inicial inválida: hay letras en la fecha. Use solo dígitos y guiones.")
                continue
            if res_ini == "SEPARADOR":
                print("Fecha inicial inválida: separadores incorrectos. Use '-' entre mes, día y año. Ejemplo: MM-DD-YYYY.")
                continue
            if res_ini is None:
                print("Formato inválido para la fecha inicial. Use MM-DD-YYYY.")
                continue
            fecha_inicio = res_ini
            break
        if cancelar_edicion:
            continue

        while True:
            try:
                texto_fin = input("Fecha final (MM-DD-YYYY) o 'X' para cancelar: ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada de fecha final.")
                cancelar_edicion = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada de fecha final.")
                cancelar_edicion = True
                break
            if texto_fin.upper() == "X":
                cancelar_edicion = True
                break
            if texto_fin == "":
                print("Fecha final inválida: campo vacío.")
                continue
            res_fin = analizar_fecha_o_none(texto_fin)
            if res_fin == "LETRAS":
                print("Fecha final inválida: hay letras en la fecha. Use solo dígitos y guiones.")
                continue
            if res_fin == "SEPARADOR":
                print("Fecha final inválida: separadores incorrectos. Use '-' entre mes, día y año. Ejemplo: MM-DD-YYYY.")
                continue
            if res_fin is None:
                print("Formato inválido para la fecha final. Use MM-DD-YYYY.")
                continue
            fecha_fin = res_fin
            break
        if cancelar_edicion:
            continue

        if fecha_fin < fecha_inicio:
            print("Rango inválido: la fecha final es anterior a la inicial.")
            continue

        registros_rango = []
        for registro_reserva in reservas:
            if fecha_inicio <= registro_reserva["fecha"] <= fecha_fin:
                cliente_encontrado = None
                for registro_cliente in clientes:
                    if registro_cliente["id"] == registro_reserva["cliente_id"]:
                        cliente_encontrado = registro_cliente
                        break
                registros_rango.append({
                    "folio": registro_reserva["folio"],
                    "fecha": registro_reserva["fecha"].strftime(FORMATO_FECHA_INPUT),
                    "cliente": f"{cliente_encontrado['apellidos']}, {cliente_encontrado['nombre']}" if cliente_encontrado else "Cliente desconocido",
                    "evento": registro_reserva["evento"]
                })
        if not registros_rango:
            print("No hay eventos en el rango solicitado.")
            continue
        tabla_rango = [[r["folio"], r["fecha"], r["cliente"], r["evento"]] for r in registros_rango]
        print("\n" + "-" * 60)
        print(f"EVENTOS DEL {fecha_inicio.strftime(FORMATO_FECHA_INPUT)} AL {fecha_fin.strftime(FORMATO_FECHA_INPUT)}".center(60))
        print("-" * 60)
        print(tabulate(tabla_rango, headers=["FOLIO", "FECHA", "CLIENTE", "EVENTO"], tablefmt="grid"))

        while True:
            try:
                sel_folio_texto = input("Indique el folio a modificar o 'X' para cancelar: ").strip()
            except EOFError:
                print("Interrupción por EOF durante selección de folio.")
                cancelar_edicion = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante selección de folio.")
                cancelar_edicion = True
                break
            if sel_folio_texto.upper() == "X":
                cancelar_edicion = True
                break
            if sel_folio_texto == "":
                print("Folio inválido: campo vacío.")
                continue
            if sel_folio_texto == "0":
                print("Folio inválido: el número debe ser mayor a 0.")
                continue
            if not sel_folio_texto.isdigit():
                print("Folio inválido: no se aceptan letras en el folio.")
                continue
            folio_seleccionado = int(sel_folio_texto)
            reserva_obj = None
            for registro_reserva in reservas:
                if registro_reserva["folio"] == folio_seleccionado and fecha_inicio <= registro_reserva["fecha"] <= fecha_fin:
                    reserva_obj = registro_reserva
                    break
            if not reserva_obj:
                print("Folio no pertenece al rango mostrado o no existe. Intente de nuevo.")
                continue
            break
        if cancelar_edicion:
            continue

        while True:
            try:
                nuevo_nombre_evento = input("Nuevo nombre de evento o 'X' para cancelar: ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada del nuevo nombre de evento.")
                cancelar_edicion = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada del nuevo nombre de evento.")
                cancelar_edicion = True
                break
            if nuevo_nombre_evento.upper() == "X":
                cancelar_edicion = True
                break
            if nuevo_nombre_evento == "":
                print("Nombre inválido: el campo está vacío.")
                continue
            if nuevo_nombre_evento.strip() == "":
                print("Nombre inválido: no se aceptan solo espacios en blanco.")
                continue
            break
        if cancelar_edicion:
            continue

        try:
            with sqlite3.connect(DB_FILE) as conexion:
                cursor = conexion.cursor()
                cursor.execute("UPDATE reservas SET evento=? WHERE folio=?", (nuevo_nombre_evento, folio_seleccionado))
                conexion.commit()
                cursor.close()
            cargar_estado_desde_bd()
            print(f"Evento con folio {folio_seleccionado} actualizado en la base de datos.")
        except Exception as err:
            print(f"Advertencia al actualizar evento en BD: {err}")
            actualizado_memoria = False
            for registro_reserva in reservas:
                if registro_reserva["folio"] == folio_seleccionado:
                    registro_reserva["evento"] = nuevo_nombre_evento
                    actualizado_memoria = True
                    break
            if actualizado_memoria:
                print(f"Evento con folio {folio_seleccionado} actualizado en memoria.")
            else:
                print("No se pudo actualizar el evento ni en BD ni en memoria (folio no encontrado).")

    elif opcion == 3:
        print("\n" + "=" * 60)
        print("CONSULTAR RESERVACIONES POR FECHA".center(60))
        print("=" * 60)

        while True:
            try:
                texto_fecha_consulta = input("Ingrese la fecha a consultar (MM-DD-YYYY) o Enter para hoy: ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada de fecha de consulta.")
                continue
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada de fecha de consulta.")
                continue

            if texto_fecha_consulta == "":
                fecha_consulta = datetime.date.today()
                print("\n" + "-" * 60)
                print("FECHA SELECCIONADA".center(60))
                print("-" * 60)
                print(f"Fecha consultada: {fecha_consulta.strftime(FORMATO_FECHA_INPUT)}")
                print("-" * 60 + "\n")
            else:
                res_consulta = analizar_fecha_o_none(texto_fecha_consulta)
                if res_consulta == "LETRAS":
                    print("Fecha inválida: hay letras en la fecha. Use solo dígitos y guiones.")
                    continue
                if res_consulta == "SEPARADOR":
                    print("Fecha inválida: separadores incorrectos. Use '-' entre mes, día y año. Ejemplo: MM-DD-YYYY.")
                    continue
                if res_consulta is None:
                    print("Fecha inválida: formato incorrecto. Use MM-DD-YYYY.")
                    continue
                fecha_consulta = res_consulta

            hay_registros = imprimir_reporte_tabular_por_fecha(fecha_consulta)
            if not hay_registros:
                print("\n" + "-" * 60)
                print("NO HAY RESERVACIONES".center(60))
                print("-" * 60)
                print(f"Fecha consultada: {fecha_consulta.strftime(FORMATO_FECHA_INPUT)}")
                print("No se encontraron reservaciones para la fecha indicada.")
                try:
                    resp_no_reg = input("Ingrese otra fecha para consultar o 'X' para cancelar: ").strip().upper()
                except EOFError:
                    print("Interrupción por EOF durante reintento de consulta.")
                    continue
                except KeyboardInterrupt:
                    print("Interrupción por teclado durante reintento de consulta.")
                    continue
                if resp_no_reg == "X":
                    break
                continue

            print("\nOpciones de exportación:")
            print("a) CSV")
            print("b) JSON")
            print("c) Excel")
            print("X) No exportar")
            while True:
                try:
                    opcion_export_texto = input("Seleccione a, b, c o X para cancelar: ").strip().upper()
                except EOFError:
                    print("Interrupción por EOF durante selección de exportación.")
                    opcion_export_texto = "X"
                except KeyboardInterrupt:
                    print("Interrupción por teclado durante selección de exportación.")
                    opcion_export_texto = "X"
                if opcion_export_texto == "" or opcion_export_texto == "X":
                    break
                if opcion_export_texto not in ("A", "B", "C"):
                    print("Opción inválida en exportación: ingrese 'a', 'b', 'c' o 'X'.")
                    continue
                filas_export = generar_reporte_por_fecha_lista(fecha_consulta)
                if opcion_export_texto == "A":
                    exportar_reporte_csv(fecha_consulta, filas_export)
                elif opcion_export_texto == "B":
                    exportar_reporte_json(fecha_consulta, filas_export)
                elif opcion_export_texto == "C":
                    exportar_reporte_excel(fecha_consulta, filas_export)
                break


            break

    elif opcion == 4:
        print("\n" + "=" * 60)
        print("REGISTRAR UN NUEVO CLIENTE".center(60))
        print("=" * 60)
        cancelar_cliente = False

        while True:
            try:
                texto_nombre = input("Ingrese el nombre del cliente (o 'X' para cancelar): ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada del nombre del cliente.")
                cancelar_cliente = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada del nombre del cliente.")
                cancelar_cliente = True
                break
            if texto_nombre.upper() == "X":
                cancelar_cliente = True
                break
            if texto_nombre == "":
                print("Nombre inválido: el campo 'Nombre' está vacío.")
                continue
            if any(char.isdigit() for char in texto_nombre):
                print("Nombre inválido: no se aceptan dígitos en el nombre.")
                continue
            if not texto_nombre.replace(" ", "").isalpha():
                print("Nombre inválido: solo letras y espacios son permitidos. Ejemplo: María")
                continue
            break
        if cancelar_cliente:
            continue

        while True:
            try:
                texto_apellidos = input("Ingrese los apellidos del cliente (o 'X' para cancelar): ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada de apellidos del cliente.")
                cancelar_cliente = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada de apellidos del cliente.")
                cancelar_cliente = True
                break
            if texto_apellidos.upper() == "X":
                cancelar_cliente = True
                break
            if texto_apellidos == "":
                print("Apellidos inválidos: el campo 'Apellidos' está vacío.")
                continue
            if any(char.isdigit() for char in texto_apellidos):
                print("Apellidos inválidos: no se aceptan dígitos en los apellidos.")
                continue
            if not texto_apellidos.replace(" ", "").isalpha():
                print("Apellidos inválidos: solo letras y espacios son permitidos. Ejemplo: García López")
                continue
            break
        if cancelar_cliente:
            continue


        cliente_id_bd = insertar_cliente_bd(texto_nombre, texto_apellidos)
        if cliente_id_bd:

            cargar_estado_desde_bd()
            print(f"Cliente registrado con ID {cliente_id_bd}.")
            continue


        print("Advertencia: no se pudo insertar el cliente en la base de datos mediante la operación estándar.")
        try:

            cliente_id_mem = next_cliente_id
            with sqlite3.connect(DB_FILE) as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT MAX(cliente_id) FROM clientes")
                max_row = cursor.fetchone()
                cursor.close()
                if max_row and max_row[0] and (max_row[0] + 1) > cliente_id_mem:
                    cliente_id_mem = max_row[0] + 1
        except Exception as err:
            print(f"Advertencia al obtener MAX(cliente_id) desde BD: {err}")

        try:
            with sqlite3.connect(DB_FILE) as conexion:
                cursor = conexion.cursor()
                cursor.execute("INSERT OR IGNORE INTO clientes(cliente_id,nombre,apellidos) VALUES(?,?,?)",
                               (cliente_id_mem, texto_nombre, texto_apellidos))
                conexion.commit()
                cursor.close()
            cargar_estado_desde_bd()
            encontrado = None
            for c in clientes:
                if c["nombre"] == texto_nombre and c["apellidos"] == texto_apellidos:
                    encontrado = c["id"]
                    break
            if encontrado:
                print(f"Cliente registrado con ID {encontrado}.")
                next_cliente_id = max(next_cliente_id, encontrado + 1)
                continue
            else:
                nuevo_cliente = {"id": cliente_id_mem, "nombre": texto_nombre, "apellidos": texto_apellidos}
                clientes.append(nuevo_cliente)
                print(f"Cliente registrado en memoria con ID {cliente_id_mem}. Atención: verifique persistencia en BD.")
                next_cliente_id = cliente_id_mem + 1
                continue
        except Exception as err:
            print(f"Error persistiendo cliente (fallback): {err}")
            cliente_id_mem = next_cliente_id
            nuevo_cliente = {"id": cliente_id_mem, "nombre": texto_nombre, "apellidos": texto_apellidos}
            clientes.append(nuevo_cliente)
            print(f"Cliente registrado en memoria con ID {cliente_id_mem}. No se pudo persistir en BD en este intento.")
            next_cliente_id = cliente_id_mem + 1
            continue

    elif opcion == 5:
        print("\n" + "=" * 60)
        print("REGISTRAR UNA SALA".center(60))
        print("=" * 60)
        cancelar_sala = False

        while True:
            try:
                texto_nombre_sala = input("Ingrese el nombre de la sala (o 'X' para cancelar): ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada del nombre de sala.")
                cancelar_sala = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada del nombre de sala.")
                cancelar_sala = True
                break
            if texto_nombre_sala.upper() == "X":
                cancelar_sala = True
                break
            if texto_nombre_sala == "":
                print("Nombre de sala inválido: campo vacío.")
                continue
            if any(char.isdigit() for char in texto_nombre_sala):
                print("Nombre de sala inválido: no se aceptan dígitos en el nombre de sala.")
                continue
            if not es_nombre_sala_valido(texto_nombre_sala):
                print("Nombre de sala inválido: solo letras y espacios permitidos. Ejemplo: Sala Ejecutiva")
                continue
            break
        if cancelar_sala:
            continue

        while True:
            try:
                texto_cupo = input("Ingrese el cupo de la sala (entero mayor a 0) o 'X' para cancelar: ").strip()
            except EOFError:
                print("Interrupción por EOF durante entrada de cupo.")
                cancelar_sala = True
                break
            except KeyboardInterrupt:
                print("Interrupción por teclado durante entrada de cupo.")
                cancelar_sala = True
                break
            if texto_cupo.upper() == "X":
                cancelar_sala = True
                break
            if texto_cupo == "":
                print("Cupo inválido: campo vacío.")
                continue
            if any(c.isalpha() for c in texto_cupo):
                print("Cupo inválido: no se aceptan letras en el cupo; introduzca un número entero mayor a 0.")
                continue
            if not texto_cupo.isdigit():
                print("Cupo inválido: formato no numérico. Ejemplo válido: 12")
                continue
            try:
                cupo_int = int(texto_cupo)
            except ValueError:
                print("Cupo inválido: no se pudo convertir a entero.")
                continue
            if cupo_int == 0:
                print("Cupo inválido: la sala no puede tener cupo 0; el número debe ser mayor a 0.")
                continue
            if cupo_int < 0:
                print("Cupo inválido: no se aceptan números negativos para el cupo.")
                continue
            break
        if cancelar_sala:
            continue

        sala_id_bd = insertar_sala_bd(texto_nombre_sala, cupo_int)
        if sala_id_bd:
            cargar_estado_desde_bd()
            print(f"Sala registrada con ID {sala_id_bd}.")
            continue
        sala_id_mem = next_sala_id
        try:
            with sqlite3.connect(DB_FILE) as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT MAX(sala_id) FROM salas")
                max_row = cursor.fetchone()
                cursor.close()
                if max_row and max_row[0] and (max_row[0] + 1) > sala_id_mem:
                    sala_id_mem = max_row[0] + 1
        except Exception as err:
            print(f"Advertencia al obtener MAX(sala_id) desde BD: {err}")
        nueva_sala = {"id": sala_id_mem, "nombre": texto_nombre_sala, "cupo": cupo_int}
        salas.append(nueva_sala)
        try:
            with sqlite3.connect(DB_FILE) as conexion:
                cursor = conexion.cursor()
                cursor.execute("INSERT OR IGNORE INTO salas(sala_id,nombre,cupo) VALUES(?,?,?)",
                               (sala_id_mem, texto_nombre_sala, cupo_int))
                conexion.commit()
                cursor.close()
        except Exception as err:
            print(f"Advertencia al intentar persistir sala con ID explícito: {err}")
        print(f"Sala registrada en memoria con ID {sala_id_mem}.")
        next_sala_id = sala_id_mem + 1

    elif opcion == 6:
        while True:
            try:
                respuesta_salir = input("¿Desea salir del programa? (S/N): ").strip().upper()
            except EOFError:
                print("Interrupción por EOF durante confirmación de salida.")
                respuesta_salir = "N"
            except KeyboardInterrupt:
                print("Interrupción por teclado durante confirmación de salida.")
                respuesta_salir = "N"
            if respuesta_salir == "":
                print("Entrada vacía: indique 'S' para salir o 'N' para cancelar.")
                continue
            if respuesta_salir not in ("S", "N"):
                print("Opción inválida: solo 'S' o 'N'.")
                continue
            break
        if respuesta_salir == "S":
            print("\n" + "=" * 60)
            print("Saliendo del programa ..... ".center(60))
            print("=" * 60)
            sys.exit()
        else:
            continue

    else:
        print("Opción no válida. Intente de nuevo.")
        continue
