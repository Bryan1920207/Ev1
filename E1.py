import pandas as pd
import datetime

diccionario_evento={"Nombre":[],
             "Cupo":[],
             "Fecha":[]}
diccionario_cliente={"Nombre":[],
             "Apellido":[]}
diccionario_sala={"Nombre":[],
             "Cupo":[]}
diccionario_datos=pd.DataFrame(diccionario_evento)
diccionario_datos=pd.DataFrame(diccionario_cliente)
diccionario_datos=pd.DataFrame(diccionario_sala)
while True:
    if diccionario_sala==0:
        pass
    else:
        break