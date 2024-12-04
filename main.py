import json
import ipaddress
import matplotlib.pyplot as plt
import networkx as nx
import threading
import time
from escanear_red import obtener_hostnames_y_interfaces, obtener_diccionario_router_ip, obtener_informacion_router, obtener_informacion_interfaces
from flask import Flask, jsonify, request
from graficacion import graficar_enlaces_entre_routers, obtener_vecinos

# Variables globales
diccionario_router_ip = {}
primera_ejecucion = True
# Variable global que determinará el tiempo de intervalo
intervalo = 5  # Intervalo inicial en minutos
# Variable de control para detener el hilo
detener_hilo = threading.Event()

app = Flask(__name__)

# Función que ejecuta la configuración SSH y escanea la red
def inicializar_red():
    print("Configurando SSH y escaneando la red")
    #Descomentar al terminar
    #configure_ssh_from_json()
    global diccionario_router_ip
    diccionario_router_ip = obtener_diccionario_router_ip()

# Función que se ejecutará periódicamente
def funcion_periodica():
    global intervalo
    while not detener_hilo.is_set():  # Comprobamos si se debe detener el hilo
        obtener_hostnames_y_interfaces()
        time.sleep(intervalo*60)

# Función para cambiar el intervalo
def cambiar_intervalo(nuevo_intervalo):
    global intervalo
    intervalo = nuevo_intervalo
    print("Nuevo intervalo:", intervalo, "segundos")

# Función para matar el hilo desde el hilo principal
def detener_hilo_secundario():
    detener_hilo.set()  # Establecemos el evento para que el hilo termine

@app.route('/topologia', methods=['GET'])
def info_routers():
    mi_diccionario = {}
    # Cargar el archivo JSON
    with open('network_info.json', 'r') as file:
        data = json.load(file)

    # Obtener las claves del diccionario
    hostnames = list(data.keys())

    for hostname in hostnames:
        vecinos = obtener_vecinos(hostname, 'network_info.json')
        mi_diccionario[hostname] = []

        for vecino in vecinos:
            mi_diccionario[hostname].append("http://127.0.0.1:5000/routers/" + vecino)
    return mi_diccionario, 200

@app.route('/topologia', methods=['POST'])
def iniciar_demonio():
    hilo_secundario = threading.Thread(target=funcion_periodica)
    hilo_secundario.start()
    return "Demonio creado", 200

@app.route('/topologia', methods=['PUT'])
def iniciar_demonio_put():
    try:
        # Obtener el número entero enviado en el cuerpo de la solicitud (asumido en JSON)
        data = request.get_json()
        
        if not data or 'intervalo' not in data:
            return "Falta el parámetro 'intervalo' en la solicitud", 400
        
        nuevo_intervalo = data['intervalo']
        
        if not isinstance(nuevo_intervalo, int):
            return "'intervalo' debe ser un número entero", 400
        
        # Cambiar el intervalo
        cambiar_intervalo(nuevo_intervalo)
        return f"Intervalo actualizado a {nuevo_intervalo} segundos.", 200
    except Exception as e:
        return f"Error al procesar la solicitud: {str(e)}", 500

@app.route('/topologia', methods=['DELETE'])
def iniciar_demonio():
    detener_hilo_secundario()
    return "Demonio muerto", 200

@app.route('/topologia/grafica', methods=['GET'])
def graficar_topologia():
    obtener_hostnames_y_interfaces()
    graficar_enlaces_entre_routers('network_info.json', 'enlaces_entre_routers.png')
    return jsonify({"message": "Grafica lista :3"}), 200

@app.route('/routers', methods=['GET'])
def obtener_informacion_routers():
    routers_info = []
    
    # Recorrer el diccionario de routers y obtener la información de cada uno
    for hostname, ip in diccionario_router_ip.items():

        print("ip: " + ip)
        # Obtener la información del router
        router_info = obtener_informacion_router(hostname, ip)
        
        if router_info:
            routers_info.append(router_info)
    
    return jsonify(routers_info)

@app.route('/routers/<hostname>/', methods=['GET'])
def obtener_informacion_router_especifico(hostname):
    # Comprobar si el hostname existe en el diccionario
    if hostname in diccionario_router_ip:
        ip = diccionario_router_ip[hostname]
        
        # Obtener la información del router
        router_info = obtener_informacion_router(hostname, ip)
        
        # Retornar la información en formato JSON
        return jsonify(router_info)
    else:
        # Si el hostname no existe, retornar un error 404
        return jsonify({"error 404": "Router no encontrado"}), 404
    
@app.route('/routers/<hostname>/interfaces', methods=['GET'])
def obtener_informacion_interfaz(hostname):
    # Comprobar si el hostname existe en el diccionario
    if hostname in diccionario_router_ip:
        # Obtener la IP del router
        ip = diccionario_router_ip[hostname]
        
        # Llamar a la función que obtiene la información de las interfaces
        resultado = obtener_informacion_interfaces(hostname, ip)
        
        # Si hay un error en la función, retornar un error 500
        if resultado is None:
            return jsonify({"error 500": "Error al obtener la información del router"}), 500

        # Convertir el resultado JSON (string) a un objeto de Python
        resultado_json = json.loads(resultado)
        
        # Eliminar el primer elemento de "interfaces"
        if "interfaces" in resultado_json and len(resultado_json["interfaces"]) > 0:
            resultado_json["interfaces"].pop(0)
        
        # Devolver la información modificada en formato JSON
        return jsonify(resultado_json), 200
    else:
        # Si el hostname no existe, retornar un error 404
        return jsonify({"error 404": "Router no encontrado"}), 404

@app.route('/api/data', methods=['POST'])
def get_data():
    data = request.get_json()  # Obtener los datos JSON enviados en la solicitud
    name = data.get('name', 'Unknown')  # Obtenemos el valor de 'name', por defecto 'Unknown'
    return jsonify({"message": f"Hello, {name}!"})

# Iniciar el servidor
if __name__ == '__main__':
    # Realizar la configuración y escaneo solo la primera vez
    if primera_ejecucion:
        
        inicializar_red()  # Llamamos a la función de configuración
        primera_ejecucion = False  # Evitamos que se vuelva a ejecutar
    
    app.run(debug=False)
