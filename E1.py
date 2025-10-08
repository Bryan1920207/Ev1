import datetime
import sys
from tabulate import tabulate

# Almacenamiento en listas
clientes = []       # cada cliente: {'id': int, 'nombre': str, 'apellidos': str}
salas = []          # cada sala: {'id': int, 'nombre': str, 'cupo': int}
reservas = []       # cada reserva: {'folio': int, 'cliente_id': int, 'sala_id': int, 'fecha': date, 'turno': str, 'evento': str}

# Contadores para IDs y folios
next_cliente_id = 1
next_sala_id = 1
next_folio = 1001

# Funcion para generar el reporte tabular de la opcion 2
def generar_reporte_por_rango(fecha_ini, fecha_fin):
    if not clientes:
        print("No hay clientes registrados. La consulta no puede realizarse.")
        return []
    if not salas:
        print("No hay salas registradas. La consulta no puede realizarse.")
        return []
    if not reservas:
        print("No hay reservaciones registradas. La consulta no puede realizarse.")
        return []

    reservas_rango = [
        r for r in reservas
        if fecha_ini <= r['fecha'] <= fecha_fin
        ]
    if not reservas_rango:
        print("No hay reservaciones en ese rango de fechas.")
        return []

    tabla = []
    for r in reservas_rango:
        cliente = next(c for c in clientes if c['id'] == r['cliente_id'])
        tabla.append([
            r['folio'],
            r['fecha'].strftime("%d-%m-%Y"),
            f"{cliente['apellidos']}, {cliente['nombre']}",
            r['evento']
        ])

    encabezado = (
        f"REPORTE DE RESERVACIONES DEL "
        f"{fecha_ini.strftime('%d-%m-%Y')} AL {fecha_fin.strftime('%d-%m-%Y')}"
    )
    print("\n" + "=" * 60)
    print(encabezado.center(60))
    print("=" * 60)
    print(tabulate(tabla, headers=["FOLIO", "FECHA", "CLIENTE", "EVENTO"], tablefmt="grid"))
    print("FIN DEL REPORTE\n")

    return reservas_rango

# Funcion para generar el reporte tabular de la opcion 3
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

    reservas_en_fecha = [r for r in reservas if r['fecha'] == fecha_consulta]
    if not reservas_en_fecha:
        print("No hay reservaciones para la fecha indicada.")
        return

    tabla = []
    for r in reservas_en_fecha:
        sala = next((s for s in salas if s['id'] == r['sala_id']), None)
        cliente = next((c for c in clientes if c['id'] == r['cliente_id']), None)
        if sala and cliente:
            tabla.append([
                sala['id'],
                f"{cliente['apellidos']}, {cliente['nombre']}",
                r['evento'],
                r['turno'].upper()
            ])

    print("\n" + "=" * 60)
    header = f"REPORTE DE RESERVACIONES PARA EL {fecha_consulta.strftime('%d-%m-%Y')}"
    print(header.center(60))
    print("=" * 60)
    print(tabulate(tabla, headers=["SALA", "CLIENTE", "EVENTO", "TURNO"], tablefmt="grid"))
    print("FIN DEL REPORTE\n")


while True:
    # Menú 
    print("\n" + "=" * 60)
    print("----- MENU PRINCIPAL -----".center(60))
    print("=" * 60)
    print("1. Registrar reservación de una sala.")
    print("2. Editar evento.")
    print("3. Consultar reservaciones por fecha.")
    print("4. Registrar un nuevo cliente.")
    print("5. Registrar una sala.")
    print("6. Salir.")
    print("=" * 60)

    try:
        opcion = int(input("Seleccionar una opción (1-6): "))
        print()
        if opcion < 1 or opcion > 6:
            raise ValueError("La opción debe ser un número entre 1 y 6.")
    except ValueError as e:
        texto = str(e)
        if "invalid literal for int()" in texto:
            print("Error de entrada: solo se aceptan números enteros.")
        else:
            print(f"Error de entrada: {texto}")
        continue
    except (EOFError, KeyboardInterrupt):
        print("\nOperación cancelada por el usuario.")
        sys.exit()
    except Exception as e:
        print(f"Error inesperado ({sys.exc_info()[0].__name__}): {e}")
        continue

    if opcion == 1:
        # Sección: Registrar reservación
        print("\n" + "=" * 60)
        print("REGISTRAR RESERVACIÓN DE UNA SALA".center(60))
        print("=" * 60)

        cancel = False

        # 1) Fecha
        while True:
            try:
                fecha_str = input("Ingrese fecha de reservación (DD-MM-YYYY) o 'X' para cancelar: ").strip()
                if fecha_str.upper() == 'X':
                    print("\n" + "=" * 60)
                    print("Operación cancelada.")
                    print("=" * 60)
                    cancel = True
                    break

                fecha = datetime.datetime.strptime(fecha_str, "%d-%m-%Y").date()
                if fecha < datetime.date.today() + datetime.timedelta(days=2):
                    print("\n" + "=" * 60)
                    print("La fecha debe ser al menos dos días posterior a hoy.")
                    print("=" * 60)
                    continue
            except ValueError:
                print("\n" + "=" * 60)
                print("Formato inválido. Use DD-MM-YYYY o 'X' para cancelar.")
                print("=" * 60)
                continue
            except (EOFError, KeyboardInterrupt):
                print("\n" + "=" * 60)
                print("Operación cancelada por el usuario.")
                print("=" * 60)
                sys.exit()
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
            for c in sorted(clientes, key=lambda x: (x['apellidos'], x['nombre'])):
                print(f"{c['id']}: {c['apellidos']}, {c['nombre']}")
                print("=" * 60)
            sel = input("Ingrese ID de cliente o 'X' para cancelar: ").strip()
            if sel.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not sel.isdigit():
                print("Entrada inválida. Solo números o 'X'.")
                continue
            cid = int(sel)
            if not any(c['id'] == cid for c in clientes):
                print("ID de cliente no existe. Intente de nuevo.")
                continue
            break
        if cancel:
            continue

        # 3) Salas disponibles
        disponibles = []
        for s in salas:
            for turno in ("Matutino", "Vespertino", "Nocturno"):
                ocupado = any(
                    r['sala_id'] == s['id'] and r['fecha'] == fecha and r['turno'] == turno
                    for r in reservas
                )
                if not ocupado:
                    disponibles.append((s['id'], s['nombre'], s['cupo'], turno))
        if not disponibles:
            print("No hay salas o turnos disponibles en esa fecha.")
            continue
        print("\n" + "=" * 60)
        print(f"Salas disponibles para {fecha.strftime('%d-%m-%Y')}".center(60))
        print("=" * 60)
        for sid, nom, cupo, turno in disponibles:
            print(f"{sid}: {nom}, cupo {cupo} - {turno}")
            print("=" * 60)

        # 4) Selección de sala y turno
        while True:
            sel = input("Ingrese ID de sala o 'X' para cancelar: ").strip()
            if sel.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not sel.isdigit():
                print("Entrada inválida. Solo números o 'X'.")
                continue
            sid = int(sel)

            if not any(s['id'] == sid for s in salas):
                print("El ID de sala no existe. Intente de nuevo.")
                continue

            turno_sel = input("Turno (Matutino/Vespertino/Nocturno) o 'X' para cancelar: ").strip().title()
            if turno_sel.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not any(sid == d[0] and turno_sel == d[3] for d in disponibles):
                print("Sala o turno inválido. Intente de nuevo.")
                continue
            break
        if cancel:
            continue

        # 5) Nombre del evento
        evento = input("Nombre del evento o 'X' para cancelar: ").strip()
        if evento.upper() == 'X':
            print("Operación cancelada.")
            continue
        if not evento:
            print("El nombre del evento no puede estar vacío.")
            continue

        # 6) Guardar
        reserva = {
            'folio': next_folio,
            'cliente_id': cid,
            'sala_id': sid,
            'fecha': fecha,
            'turno': turno_sel,
            'evento': evento
        }
        reservas.append(reserva)
        print("\n" + "=" * 60)
        print(f"Reservación registrada con folio {next_folio}.")
        print("Reservación generada exitosamente.")
        print("=" * 60)
        next_folio += 1

    elif opcion == 2:
        # Sección: Editar evento
        print("\n" + "=" * 60)
        print("EDITAR NOMBRE DE UN EVENTO".center(60))
        print("=" * 60)

        cancel = False
        try:
            ini = input("Fecha inicial (DD-MM-YYYY) o 'X' para cancelar: ").strip()
            if ini.upper() == 'X': raise KeyboardInterrupt
            fecha_ini = datetime.datetime.strptime(ini, "%d-%m-%Y").date()

            fin = input("Fecha final   (DD-MM-YYYY) o 'X' para cancelar: ").strip()
            if fin.upper() == 'X': raise KeyboardInterrupt
            fecha_fin = datetime.datetime.strptime(fin, "%d-%m-%Y").date()

            if fecha_fin < fecha_ini:
                print("Rango inválido: la fecha final es anterior a la inicial.")
                continue

        except ValueError:
            print("Formato inválido. Use DD-MM-YYYY.")
            continue
        except (EOFError, KeyboardInterrupt):
            print("Operación cancelada.")
            continue

        eventos = generar_reporte_por_rango(fecha_ini, fecha_fin)
        if not eventos:
            continue

        # Seleccionar folio
        while True:
            sel = input("Folio a modificar o 'X' para cancelar: ").strip()
            if sel.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not sel.isdigit():
                print("Entrada inválida. Solo números o 'X'.")
                continue
            folio_sel = int(sel)
            reserva = next((r for r in eventos if r['folio'] == folio_sel), None)
            if not reserva:
                print("Folio no pertenece al listado. Intente de nuevo.")
                continue
            break
        if cancel:
            continue

        # Nuevo nombre
        while True:
            nuevo = input("Nuevo nombre de evento o 'X' para cancelar: ").strip()
            if nuevo.upper() == 'X':
                print("Operación cancelada.")
                cancel = True
                break
            if not nuevo:
                print("El nombre del evento no puede quedar vacío.")
                continue
            reserva['evento'] = nuevo
            break
        if cancel:
            continue

        print("\n" + "=" * 60)
        print(f"Evento con folio {reserva['folio']} actualizado exitosamente.")
        print("=" * 60)

    elif opcion == 3:
        # Sección: Consultar por fecha
        print("\n" + "=" * 60)
        print("CONSULTAR RESERVACIONES POR FECHA".center(60))
        print("=" * 60)

        try:
            fecha_str = input("Ingrese la fecha a consultar (DD-MM-YYYY): ").strip()
            fecha_consulta = datetime.datetime.strptime(fecha_str, "%d-%m-%Y").date()
        except ValueError:
            print("Formato inválido. Use DD-MM-YYYY.")
            continue
        except (EOFError, KeyboardInterrupt):
            print("Operación cancelada por el usuario.")
            sys.exit()

        print("\n" + "=" * 60)
        generar_reporte_por_fecha(fecha_consulta)
        print("=" * 60)
    elif opcion == 4:
        # Sección: Registrar un nuevo cliente
        print("\n" + "=" * 60)
        print("REGISTRAR UN NUEVO CLIENTE".center(60))
        print("=" * 60)

        try:
            nombre    = input("Ingrese el nombre del cliente: ").strip()

            # Validar no vacío para nombre
            if not nombre:
                raise ValueError("Nombre no puede estar vacío.")

            # Validar solo letras y espacios para nombre
            if not (nombre.replace(" ", "").isalpha()):
                raise ValueError("Nombre solo debe contener letras.")

            apellidos = input("Ingrese los apellidos del cliente: ").strip()

            # Validar no vacío para apellidos
            if not apellidos:
                raise ValueError("Apellidos no puede estar vacío.")

            # Validar solo letras y espacios para apellidos
            if not (apellidos.replace(" ", "").isalpha()):
                raise ValueError("Apellidos solo debe contener letras.")

            # Construir y guardar cliente
            nuevo = {
                'id': next_cliente_id,
                'nombre': nombre,
                'apellidos': apellidos
            }
            clientes.append(nuevo)

            # Confirmación
            print("\n" + "=" * 60)
            print(f"Cliente registrado con ID {next_cliente_id}.".center(60))
            print("Cliente agregado exitosamente.".center(60))
            print("=" * 60)

            next_cliente_id += 1

        except ValueError as e:
            print(f"Error de entrada: {e}")
        except Exception as e:
            print(f"Error inesperado ({sys.exc_info()[0].__name__}): {e}")


    elif opcion == 5:
        # Sección: Registrar una sala
        print("\n" + "=" * 60)
        print("REGISTRAR UNA SALA".center(60))
        print("=" * 60)

        try:
            nombre_sala = input("Ingrese el nombre de la sala: ").strip()
            cupo_str   = input("Ingrese el cupo de la sala: ").strip()

            try:
                cupo = int(cupo_str)
            except ValueError:
                print("El cupo debe ser un número entero válido.")
                continue

            # Validar no vacío
            if not nombre_sala:
                raise ValueError("El nombre de la sala no puede estar vacío.")

            # Validar letras y espacios
            if not all(c.isalpha() or c.isspace() for c in nombre_sala):
                raise ValueError("El nombre solo debe contener letras y espacios.")

            # Validar cupo
            cupo = int(cupo_str)
            if cupo <= 0:
                raise ValueError("El cupo debe ser un número mayor que 0.")

            # Construir y guardar sala
            nueva = {
                'id': next_sala_id,
                'nombre': nombre_sala,
                'cupo': cupo
            }
            salas.append(nueva)

            # Confirmación
            print("\n" + "=" * 60)
            print(f"Sala registrada con ID {next_sala_id}.".center(60))
            print("Sala registrada exitosamente.".center(60))
            print("=" * 60)

            next_sala_id += 1

        except ValueError as e:
            print(f"Error de entrada: {e}")
        except Exception as e:
            print(f"Error inesperado ({sys.exc_info()[0].__name__}): {e}")


    elif opcion == 6:
        # Sección: Salir
        print("\n" + "=" * 60)
        print("SALIR DEL PROGRAMA".center(60))
        print("=" * 60)

        while True:
            try:
                respuesta = input("¿Desea salir del programa? (S/N): ").strip().upper()
                if respuesta not in ('S', 'N'):
                    raise ValueError("Solo se permiten ‘S’ o ‘N’.")
            except ValueError as e:
                print(f"Error de entrada: {e}")
                continue
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada por el usuario.")
                sys.exit()
            except Exception as e:
                print(f"Error inesperado ({sys.exc_info()[0].__name__}): {e}")
                continue

            if respuesta == 'S':
                print("\n" + "=" * 60)
                print("Saliendo del programa.....".center(60))
                print("=" * 60)
                sys.exit()
            else:
                print("\n" + "=" * 60)
                print("Regresando al menú.....".center(60))
                print("=" * 60)
                break   