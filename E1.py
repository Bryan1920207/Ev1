import datetime
import sys
from tabulate import tabulate
import json
import sqlite3
from sqlite3 import Error

# Almacenamiento en listas
clientes = []      # cada cliente: {'id': int, 'nombre': str, 'apellidos': str}
salas = []         # cada sala: {'id': int, 'nombre': str, 'cupo': int}
reservas = []      # cada reserva: {'folio': int, 'cliente_id': int, 'sala_id': int, 'fecha': date, 'turno': str, 'evento': str}

# Contadores para IDs y folios
next_cliente_id = 1
next_sala_id = 1
next_folio = 1001

# Archivo que persiste el estado de la aplicación (clientes, salas, reservas y contadores).
# Se guarda como JSON para poder reconstruir las estructuras al reiniciar el programa.
ARCHIVO_ESTADO = "estado_reservas.json"

# --- Helpers lógicos (en español y con parámetros descriptivos) ---
def analizar_fecha_o_none(texto_fecha):
    try:
        return datetime.datetime.strptime(texto_fecha, "%d-%m-%Y").date()
    except ValueError:
        return None

def es_entero_positivo_str(texto_numero):
    return texto_numero.isdigit() and int(texto_numero) > 0

def es_nombre_valido(texto_nombre):
    return bool(texto_nombre) and texto_nombre.replace(" ", "").isalpha()

def es_nombre_sala_valido(texto_nombre_sala):
    return bool(texto_nombre_sala) and all(car.isalpha() or car.isspace() for car in texto_nombre_sala)

# Funciones de reporte 
def generar_reporte_por_rango(fecha_inicio, fecha_fin):
    if not clientes:
        print("No hay clientes registrados. La consulta no puede realizarse.")
        return []

    if not salas:
        print("No hay salas registradas. La consulta no puede realizarse.")
        return []

    if not reservas:
        print("No hay reservaciones registradas. La consulta no puede realizarse.")
        return []

    reservas_rango = [reserva_item for reserva_item in reservas if fecha_inicio <= reserva_item['fecha'] <= fecha_fin]

    if not reservas_rango:
        print("No hay reservaciones en ese rango de fechas.")
        return []

    tabla = []
    for reserva_item in reservas_rango:
        cliente_item = next(cliente_item for cliente_item in clientes if cliente_item['id'] == reserva_item['cliente_id'])
        tabla.append([
            reserva_item['folio'],
            reserva_item['fecha'].strftime("%d-%m-%Y"),
            f"{cliente_item['apellidos']}, {cliente_item['nombre']}",
            reserva_item['evento']
        ])

    encabezado = (
        f"REPORTE DE RESERVACIONES DEL "
        f"{fecha_inicio.strftime('%d-%m-%Y')} AL {fecha_fin.strftime('%d-%m-%Y')}"
    )
    print("\n" + "=" * 60)
    print(encabezado.center(60))
    print("=" * 60)
    print(tabulate(tabla, headers=["FOLIO", "FECHA", "CLIENTE", "EVENTO"], tablefmt="grid"))
    print("FIN DEL REPORTE\n")

    return reservas_rango

def generar_reporte_por_fecha(fecha_consulta):
    if not clientes:
        print("No hay clientes registrados. La consulta no puede realizarse.")
        return
    if not salas:
        print("No hay salas registradas. La consulta no puede realizarse.")
        return
    if not reservas:
        print("No hay reservaciones registradas. La consulta no puede realizarse.")
        return

    reservas_en_fecha = [reserva_item for reserva_item in reservas if reserva_item['fecha'] == fecha_consulta]
    if not reservas_en_fecha:
        print("No hay reservaciones para la fecha indicada.")
        return

    tabla = []
    for reserva_item in reservas_en_fecha:
        sala_item = next((sala_item for sala_item in salas if sala_item['id'] == reserva_item['sala_id']), None)
        cliente_item = next((cliente_item for cliente_item in clientes if cliente_item['id'] == reserva_item['cliente_id']), None)
        if sala_item and cliente_item:
            tabla.append([
                sala_item['id'],
                f"{cliente_item['apellidos']}, {cliente_item['nombre']}",
                reserva_item['evento'],
                reserva_item['turno'].upper()
            ])

    print("\n" + "=" * 60)
    header = f"REPORTE DE RESERVACIONES PARA EL {fecha_consulta.strftime('%d-%m-%Y')}"
    print(header.center(60))
    print("=" * 60)
    print(tabulate(tabla, headers=["SALA", "CLIENTE", "EVENTO", "TURNO"], tablefmt="grid"))
    print("FIN DEL REPORTE\n")

def exportar_reporte_por_fecha_json(fecha_consulta):
    filas = []
    for reserva_item in reservas:
        if reserva_item['fecha'] == fecha_consulta:
            sala_item = next((sala_item for sala_item in salas if sala_item['id'] == reserva_item['sala_id']), None)
            cliente_item = next((cliente_item for cliente_item in clientes if cliente_item['id'] == reserva_item['cliente_id']), None)
            if sala_item and cliente_item:
                filas.append({
                    "sala": sala_item['id'],
                    "cliente": f"{cliente_item['apellidos']}, {cliente_item['nombre']}",
                    "evento": reserva_item['evento'],
                    "turno": reserva_item['turno'].upper()
                })
    if not filas:
        print("No hay datos para exportar en esa fecha.")
        return
    nombre = f"reporte_{fecha_consulta.strftime('%Y%m%d')}.json"
    try:
        with open(nombre, "w", encoding="utf-8") as f:
            json.dump(filas, f, ensure_ascii=False, indent=2)
        print(f"Reporte JSON guardado como {nombre}.")
    except Exception as e:
        print(f"Error al exportar JSON: {e}")

# Cargar estado inicial si existe
try:
    with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
        estado = json.load(f)
    # Reconstruir estructuras desde JSON
    clientes = estado.get("clientes", [])
    salas = estado.get("salas", [])
    reservas = [
        {
            "folio": r["folio"],
            "cliente_id": r["cliente_id"],
            "sala_id": r["sala_id"],
            "fecha": datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date(),
            "turno": r["turno"],
            "evento": r["evento"]
        } for r in estado.get("reservas", [])
    ]
    # Restaurar contadores
    next_cliente_id = estado.get("next_cliente_id", next_cliente_id)
    next_sala_id = estado.get("next_sala_id", next_sala_id)
    next_folio = estado.get("next_folio", next_folio)
    print("=" * 60)
    print(f"Estado recuperado desde {ARCHIVO_ESTADO}.".center(60))
    print("=" * 60)
except FileNotFoundError:
    print("=" * 60)
    print("No se encontró estado previo. Iniciando con estado vacío.".center(60))
    print("=" * 60)
except Exception as e:
    print("-" * 60)
    print(f"Error al cargar estado: {e}. Iniciando con estado vacío.")
    print("-" * 60)

# Bucle principal
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

    # lectura del menú con validación
    while True:
        try:
            try:
                with sqlite3.connect("Evidencia.db") as conn:
                    print(sqlite3.version)
                    mi_cursor = conn.cursor()
                    mi_cursor.execute("CREATE TABLE IF NOT EXISTS sala (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, cupo INTEGER NOT NULL);")
                    print("Tabla creada exitosamente")
            except Error as e:
                print (e)
            except:
                print(f"Se produjo el siguiente error: {sys.exc_info()[0]}")
            
            sel_opcion = input("Seleccionar una opción (1-6): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOperación cancelada por el usuario.")
            sys.exit()
        if not sel_opcion.isdigit():
            print("Error de entrada: solo se aceptan números enteros entre 1 y 6.")
            continue
        opcion = int(sel_opcion)
        if opcion < 1 or opcion > 6:
            print("Error de entrada: solo se aceptan números enteros entre 1 y 6.")
            continue
        break

    if opcion == 1:
        # Registrar reservación
        print("\n" + "=" * 60)
        print("REGISTRAR RESERVACIÓN DE UNA SALA".center(60))
        print("=" * 60)

        cancel = False

        # 1) Fecha
        while True:
            try:
                texto_fecha = input("Ingrese fecha de reservación (DD-MM-YYYY) o 'X' para cancelar:\n").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if texto_fecha.upper() == 'X':
                fecha_consultar = texto_fecha
                fecha_consultar = datetime.datetime.strptime(fecha_consultar, "%d/%m/%Y").date()

                try:
                    with sqlite3.connect("Evidencia.db",
                                        detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
                        mi_cursor = conn.cursor()
                        criterios = {"fecha":fecha_consultar}
                        mi_cursor.execute("SELECT clave, nombre, fecha_registro FROM Amigo \
                        WHERE DATE(fecha_registro) = :fecha;", criterios)
                        registros = mi_cursor.fetchall()

                        if registros:
                            pass
                        else:
                            pass

                except sqlite3.Error as e:
                    print (e)
                except Exception:
                    print(f"Se produjo el siguiente error: {sys.exc_info()[0]}")
                print("\n" + "=" * 60)
                print("Operación cancelada.")
                print("=" * 60)
                cancel = True
                break
            fecha = analizar_fecha_o_none(texto_fecha)
            if fecha is None:
                print("\n" + "=" * 60)
                print("Formato inválido. Use DD-MM-YYYY o 'X' para cancelar.")
                print("=" * 60)
                continue
            if fecha < datetime.date.today() + datetime.timedelta(days=2):
                print("\n" + "=" * 60)
                print("La fecha debe ser al menos dos días posterior a hoy.")
                print("=" * 60)
                continue
            break
        if cancel:
            continue

        # 2) Cliente
        print("\n" + "=" * 60)
        print("Clientes registrados".center(60))
        print("=" * 60)
        while True:
            if not clientes:
                print("No hay clientes registrados.")
                cancel = True
                break
            for cliente_item in sorted(clientes, key=lambda x: (x['apellidos'], x['nombre'])):
                print(f"{cliente_item['id']}: {cliente_item['apellidos']}, {cliente_item['nombre']}")
            print("=" * 60)
            try:
                sel_cliente = input("Ingrese ID de cliente o 'X' para cancelar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if sel_cliente.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not sel_cliente.isdigit():
                print("Entrada inválida. Solo números o 'X'.")
                continue
            cliente_id = int(sel_cliente)
            if not any(cliente_item['id'] == cliente_id for cliente_item in clientes):
                print("ID de cliente no existe. Intente de nuevo.")
                continue
            break
        if cancel:
            continue

        # 3) Salas disponibles 
        disponibles = []
        for sala_item in salas:
            for turno in ("Matutino", "Vespertino", "Nocturno"):
                ocupado = any(
                    reserva_item['sala_id'] == sala_item['id'] and reserva_item['fecha'] == fecha and reserva_item['turno'] == turno
                    for reserva_item in reservas
                )
                if not ocupado:
                    disponibles.append((sala_item['id'], sala_item['nombre'], sala_item['cupo'], turno))

        if not disponibles:
            print("No hay salas disponibles en esa fecha.")
            continue
        print("\n" + "=" * 60)
        print(f"Salas disponibles para {fecha.strftime('%d-%m-%Y')}".center(60))
        print("=" * 60)
        for sala_id, nombre_sala, cupo_sala, turno_disponible in disponibles:
            print(f"{sala_id}: {nombre_sala}, cupo {cupo_sala} - {turno_disponible}")
        print("=" * 60)

        # 4) Selección de sala y turno 
        while True:
            try:
                sel_sala_id = input("Ingrese ID de sala o 'X' para cancelar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if sel_sala_id.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not sel_sala_id.isdigit():
                print("Entrada inválida. Solo números o 'X'.")
                continue
            sala_id = int(sel_sala_id)
            if not any(sala_item['id'] == sala_id for sala_item in salas):
                print("El ID de sala no existe. Intente de nuevo.")
                continue

            # =menu
            print("\nSeleccione el turno:")
            print("1. Matutino")
            print("2. Vespertino")
            print("3. Nocturno")
            print("X. Cancelar")

            while True:
                try:
                    turno_opc = input("Elija el número de turno (1-3) o 'X': ").strip().upper()
                except (EOFError, KeyboardInterrupt):
                    print("\nOperación cancelada por el usuario.")
                    sys.exit()

                if turno_opc == 'X':
                    print("Operación cancelada.")
                    cancel = True
                    break
                if not turno_opc.isdigit() or int(turno_opc) not in (1, 2, 3):
                    print("Entrada inválida. Ingrese 1, 2, 3 o 'X'.")
                    continue

                turno_dict = {1: "Matutino", 2: "Vespertino", 3: "Nocturno"}
                turno_seleccionado = turno_dict[int(turno_opc)]

                # Verificar sala existe (seguridad)
                if not any(sala_item['id'] == sala_id for sala_item in salas):
                    print("Sala inválida. Verifique el ID.")
                    continue

                # Verificar si el turno ya está ocupado para esa sala y fecha
                if any(reserva_item['sala_id'] == sala_id and reserva_item['fecha'] == fecha and reserva_item['turno'] == turno_seleccionado for reserva_item in reservas):
                    print("Turno ocupado para esa sala en la fecha indicada.")
                    continue
                break
            if cancel:
                break
    # fin de menu

            break
        if cancel:
            continue


        # 5) Nombre del evento
        while True:
            try:
                evento = input("Nombre del evento o 'X' para cancelar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if evento.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            # Evitar solo espacios en blanco
            if not evento or evento.strip() == "":
                print("El nombre del evento no puede estar vacío. Intente de nuevo.")
                continue
            break
        if cancel:
            continue

        # 6) Guardar
        reserva = {
            'folio': next_folio,
            'cliente_id': cliente_id,
            'sala_id': sala_id,
            'fecha': fecha,
            'turno': turno_seleccionado,
            'evento': evento
        }
        reservas.append(reserva)
        print("\n" + "=" * 60)
        print(f"Reservación registrada con folio {next_folio}.")
        print("Reservación generada exitosamente.")
        print("=" * 60)
        next_folio += 1

    elif opcion == 2:
        # Editar evento: pedir fecha inicial y final — repetir solo esas líneas hasta válidas o X
        print("\n" + "=" * 60)
        print("EDITAR NOMBRE DE UN EVENTO".center(60))
        print("=" * 60)

        # fecha inicial
        while True:
            try:
                texto_ini = input("Fecha inicial (DD-MM-YYYY) o 'X' para cancelar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if texto_ini.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            fecha_ini = analizar_fecha_o_none(texto_ini)
            if fecha_ini is None:
                print("Formato inválido. Use DD-MM-YYYY o 'X'.")
                continue
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        # fecha final
        while True:
            try:
                texto_fin = input("Fecha final (DD-MM-YYYY) o 'X' para cancelar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if texto_fin.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            fecha_fin = analizar_fecha_o_none(texto_fin)
            if fecha_fin is None:
                print("Formato inválido. Use DD-MM-YYYY o 'X'.")
                continue
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        if fecha_fin < fecha_ini:
            print("Rango inválido: la fecha final es anterior a la inicial.")
            continue

        eventos = generar_reporte_por_rango(fecha_ini, fecha_fin)
        if not eventos:
            continue

        # Seleccionar folio
        while True:
            try:
                sel_folio = input("Folio a modificar o 'X' para cancelar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if sel_folio.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not sel_folio.isdigit():
                print("Entrada inválida. Solo números o 'X'.")
                continue
            folio_sel = int(sel_folio)
            reserva_item = next((reserva_item for reserva_item in eventos if reserva_item['folio'] == folio_sel), None)
            if not reserva_item:
                print("Folio no pertenece al listado. Intente de nuevo.")
                continue
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        # Nuevo nombre
        while True:
            try:
                nuevo = input("Nuevo nombre de evento o 'X' para cancelar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if nuevo.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not nuevo:
                print("El nombre del evento no puede quedar vacío.")
                continue
            reserva_item['evento'] = nuevo
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        print("\n" + "=" * 60)
        print(f"Evento con folio {reserva_item['folio']} actualizado exitosamente.")
        print("=" * 60)

    elif opcion == 3:
        # Consultar por fecha
        print("\n" + "=" * 60)
        print("CONSULTAR RESERVACIONES POR FECHA".center(60))
        print("=" * 60)

        while True:
            try:
                texto_fecha_consulta = input("Ingrese la fecha a consultar (DD-MM-YYYY) o 'X' para cancelar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if texto_fecha_consulta.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            fecha_consulta = analizar_fecha_o_none(texto_fecha_consulta)
            if fecha_consulta is None:
                print("Formato inválido. Use DD-MM-YYYY o 'X'.")
                continue
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        print("\n" + "=" * 60)
        generar_reporte_por_fecha(fecha_consulta)
        print("=" * 60)

        reservas_para_fecha = [reserva_item for reserva_item in reservas if reserva_item['fecha'] == fecha_consulta]
        if not reservas_para_fecha:
            print("No hay datos para exportar en esa fecha, no se preguntará por JSON.")
            continue

        # Validar respuesta para exportar
        while True:
            try:
                resp_export = input("¿Desea exportar este reporte a JSON? (S/N): ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación de exportación cancelada por el usuario.")
                resp_export = 'N'
                break
            # No aceptar entrada vacía
            if resp_export == "":
                print("Entrada vacía. Introduzca 'S' para sí o 'N' para no.")
                continue
            # Aceptar solamente letras
            if not resp_export.isalpha():
                print("Entrada inválida. Solo se permiten letras 'S' o 'N'.")
                continue
            # Aceptar solo S o N
            if resp_export not in ('S', 'N'):
                print("Opción no válida. Introduzca 'S' para sí o 'N' para no.")
                continue
            break

        if resp_export == 'S':
            exportar_reporte_por_fecha_json(fecha_consulta)

    elif opcion == 4:
        # Registrar nuevo cliente
        print("\n" + "=" * 60)
        print("REGISTRAR UN NUEVO CLIENTE".center(60))
        print("=" * 60)

        # nombre
        while True:
            try:
                texto_nombre = input("Ingrese el nombre del cliente (o 'X' para cancelar): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if texto_nombre.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not es_nombre_valido(texto_nombre):
                print("Nombre inválido. Solo letras y espacios, no vacío.")
                continue
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        # apellidos 
        while True:
            try:
                texto_apellidos = input("Ingrese los apellidos del cliente (o 'X' para cancelar): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if texto_apellidos.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not es_nombre_valido(texto_apellidos):
                print("Apellidos inválidos. Solo letras y espacios, no vacío.")
                continue
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        nuevo_cliente = {'id': next_cliente_id, 'nombre': texto_nombre, 'apellidos': texto_apellidos}
        clientes.append(nuevo_cliente)
        print("\n" + "=" * 60)
        print(f"Cliente registrado con ID {next_cliente_id}.".center(60))
        print("Cliente agregado exitosamente.".center(60))
        print("=" * 60)
        next_cliente_id += 1

    elif opcion == 5:
        # Registrar una sala
        print("\n" + "=" * 60)
        print("REGISTRAR UNA SALA".center(60))
        print("=" * 60)

        while True:
            try:
                texto_nombre_sala = input("Ingrese el nombre de la sala (o 'X' para cancelar): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if texto_nombre_sala.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not es_nombre_sala_valido(texto_nombre_sala):
                print("El nombre solo debe contener letras y espacios y no puede quedar vacío.")
                continue
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        while True:
            try:
                texto_cupo = input("Ingrese el cupo de la sala (o 'X' para cancelar): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if texto_cupo.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not texto_cupo:
                print("El cupo no puede quedar vacío.")
                continue
            if not texto_cupo.isdigit():
                print("El cupo debe ser un número entero mayor que 0.")
                continue
            cupo = int(texto_cupo)
            if cupo <= 0:
                print("El cupo debe ser un número mayor que 0.")
                continue
            break
        if 'cancel' in locals() and cancel:
            del cancel
            continue

        nueva_sala = {'id': next_sala_id, 'nombre': texto_nombre_sala, 'cupo': cupo}
        salas.append(nueva_sala)
        print("\n" + "=" * 60)
        print(f"Sala registrada con ID {next_sala_id}.".center(60))
        print("Sala registrada exitosamente.".center(60))
        print("=" * 60)
        next_sala_id += 1

        nuevo_nombre = texto_nombre_sala
        nuevo_cupo = texto_cupo
        try:
            with sqlite3.connect("AutoDemo.db") as conn:
                mi_cursor = conn.cursor()
                valores = (nuevo_nombre, nuevo_cupo) #No se incluye dato para la PK
                mi_cursor.execute("INSERT INTO sala (nombre, cupo) \
                VALUES(?,?)", valores)
        except Error as e:
            print (e)
        except Exception:
            print(f"Se produjo el siguiente error: {sys.exc_info()[0]}")

    elif opcion == 6:
        # Salir: confirmar S/N y guardar estado
        print("\n" + "=" * 60)
        print("SALIR DEL PROGRAMA".center(60))
        print("=" * 60)
        while True:
            try:
                respuesta = input("¿Desea salir del programa? (S/N): ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            if respuesta not in ('S', 'N'):
                print("Solo se permiten 'S' o 'N'.")
                continue
            break
        if respuesta == 'S':
            # Guardar estado antes de salir
            estado_a_guardar = {
                "clientes": clientes,
                "salas": salas,
                "reservas": [
                    {
                        "folio": r["folio"],
                        "cliente_id": r["cliente_id"],
                        "sala_id": r["sala_id"],
                        "fecha": r["fecha"].strftime("%Y-%m-%d"),
                        "turno": r["turno"],
                        "evento": r["evento"]
                    } for r in reservas
                ],
                "next_cliente_id": next_cliente_id,
                "next_sala_id": next_sala_id,
                "next_folio": next_folio
            }
            try:
                with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
                    json.dump(estado_a_guardar, f, ensure_ascii=False, indent=2)
                print(f"Estado guardado en {ARCHIVO_ESTADO}.")
            except Exception as e:
                print(f"Error al guardar estado: {e}")
            print("\n" + "=" * 60)
            print("Saliendo del programa ..... ".center(60))
            print("=" * 60)
            sys.exit()
        else:
            print("\n" + "=" * 60)
            print("Regresando al menú ..... ".center(60))
            print("=" * 60)

    else:
        print("Opción no válida. Intente de nuevo.")