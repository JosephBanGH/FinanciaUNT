import json
j= [{'d':['adw','wd']}]
data = j[0]['d']
respuesta = 'Operaciones hechas:'
for d in data:
    respuesta += '\n- '+d
print(respuesta)