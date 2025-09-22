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
print("1.Registrar cliente\n2.Registrar sala\n3.Editar reservacion\n4.Salir")
opcion=int(input("Que opcion desea hacer? "))
while True:
    if opcion==1:
        pass
    elif opcion==2:
        pass
    elif opcion==3:
        break