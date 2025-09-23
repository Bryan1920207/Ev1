import pandas as pd
import datetime

diccionario_evento={"Nombre":["Conferencia","Reunion",""],
             "Cupo":[50,100,275],
             "Fecha":["10/01/2020","//","//"]}
diccionario_cliente={"Nombre":["","",""],
             "Apellido":["","",""]}
diccionario_sala={"Nombre":["","",""],
             "Cupo":[50,100,275],
             "Turno":["M","N","V"]}
if diccionario_sala["Turno"] not in "MNVmnv":
    print("Turno invalido")
    
datetime.datetime.strptime(diccionario_evento["Fecha"], "%d/%m/%Y").date()
if pd.DataFrame(diccionario_evento["Cupo"]<=diccionario_sala["Cupo"]):
    pass
diccionario_datos=pd.DataFrame(diccionario_evento)
diccionario_datos=pd.DataFrame(diccionario_cliente)
diccionario_datos=pd.DataFrame(diccionario_sala)
print("1.Registrar reservacion de una sala\n2.Editar nombre de un evento\n3.Consultar reservaciones por fecha\n4.Registrar nuevo cliente\n5.Registrar sala\n6.Salir")
opcion=int(input("Que opcion desea hacer? "))
while True:
    if opcion==1:
        pass
    elif opcion==2:
        pass
    elif opcion==3:
        pass
    elif opcion==4:
        pass
    elif opcion==5:
        pass
    elif opcion==6:
        break