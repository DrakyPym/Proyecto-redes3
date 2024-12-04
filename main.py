import json
import ipaddress
import matplotlib.pyplot as plt
import networkx as nx
import threading
import time
from escanear_red import obtener_hostnames_y_interfaces, obtener_diccionario_router_ip, obtener_informacion_router, obtener_informacion_interfaces
from flask import Flask, jsonify, request
from graficacion import graficar_enlaces_entre_routers, obtener_vecinos
from configuracion_ssh import configure_ssh_from_json
from usuarios import leer_usuarios_con_permisos
from usuarios import agregar_usuario
from usuarios import eliminar_usuario
from usuarios import actualizar_usuario
from crud_usuarios_routers import crear_conexion, obtener_usuarios, agregar_usuario, actualizar_usuario, eliminar_usuario


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
    configure_ssh_from_json()
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
    return "Demonio creado\n", 200

@app.route('/topologia', methods=['PUT'])
def demonio_put():
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
        return f"Intervalo actualizado a {nuevo_intervalo} segundos.\n", 200
    except Exception as e:
        return f"Error al procesar la solicitud: {str(e)}\n", 500

@app.route('/topologia', methods=['DELETE'])
def demonio_delete():
    detener_hilo_secundario()
    return "Demonio muerto\n", 200

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
    
@app.route('/routers/<hostname>/usuarios', methods=['GET'])
def obtener_informacion_usuarios(hostname):
    cliente = crear_conexion()
    
    # Verificar si el router existe en el diccionario
    if hostname in diccionario_router_ip:
        usuarios = obtener_usuarios(cliente, hostname)
        
        if usuarios:
            return jsonify(usuarios), 200
        else:
            return jsonify({"error": "No se encontraron usuarios en este router"}), 404
    else:
        return jsonify({"error": "Router no encontrado"}), 404

@app.route('/routers/<hostname>/usuarios', methods=['POST'])
def agregar_usuario_router(hostname):
    cliente = crear_conexion()
    data = request.get_json()
    
    # Extraer los parámetros del cuerpo de la solicitud
    nombre = data.get('nombre')
    password = data.get('password')
    privilegios = data.get('privilegios', '15')
    
    # Validar la entrada
    if not nombre or not password:
        return jsonify({"error": "Faltan los parámetros 'nombre' y 'password"}), 400

    # Llamar a la función para agregar el usuario
    resultado = agregar_usuario(cliente, hostname, nombre, password, privilegios)
    
    if resultado:
        return jsonify({"mensaje": "Usuario agregado correctamente"}), 201
    else:
        return jsonify({"error": "Error al agregar el usuario"}), 500

@app.route('/routers/<hostname>/usuarios', methods=['PUT'])
def actualizar_usuario_router(hostname):
    cliente = crear_conexion()
    data = request.get_json()
    
    # Extraer los parámetros de la solicitud
    nombre = data.get('nombre')
    password = data.get('password')
    privilegios = data.get('privilegios')

    # Validar la entrada
    if not nombre or not password:
        return jsonify({"error": "Faltan los parámetros 'nombre' y 'password"}), 400

    if hostname in diccionario_router_ip:
        # Llamar a la función para actualizar el usuario
        resultado = actualizar_usuario(cliente, hostname, nombre, password, privilegios)
        
        if resultado:
            return jsonify({"mensaje": "Usuario actualizado correctamente"}), 200
        else:
            return jsonify({"error": "Error al actualizar el usuario"}), 500
    else:
        return jsonify({"error": "Router no encontrado"}), 404

@app.route('/routers/<hostname>/usuarios', methods=['DELETE'])
def eliminar_usuario_router(hostname):
    cliente = crear_conexion()
    data = request.get_json()
    
    # Extraer el nombre del usuario
    nombre = data.get('nombre')
    
    # Validar la entrada
    if not nombre:
        return jsonify({"error": "Falta el parámetro 'nombre'"}), 400
    
    if hostname in diccionario_router_ip:
        # Llamar a la función para eliminar el usuario
        resultado = eliminar_usuario(cliente, hostname, nombre)
        
        if resultado:
            return jsonify({"mensaje": "Usuario eliminado correctamente"}), 200
        else:
            return jsonify({"error": "Error al eliminar el usuario"}), 500
    else:
        return jsonify({"error": "Router no encontrado"}), 404

@app.route('/api/data', methods=['POST'])
def get_data():
    data = request.get_json()  # Obtener los datos JSON enviados en la solicitud
    name = data.get('name', 'Unknown')  # Obtenemos el valor de 'name', por defecto 'Unknown'
    return jsonify({"message": f"Hello, {name}!"})

# Ruta para obtener los usuarios de todos los routers
@app.route('/usuarios', methods=['GET'])
def obtener_usuarios():
    usuarios = []
    for ip in diccionario_router_ip.values():
        usuarios_router = leer_usuarios_con_permisos(ip)
        if usuarios_router:
            usuarios.extend(usuarios_router)
    return jsonify(usuarios)

# Ruta para agregar un usuario a los routers
@app.route('/usuarios', methods=['POST'])
def agregar_usuario_api():
    data = request.get_json()
    nombre = data.get('nombre')
    password = data.get('password')
    privilegios = data.get('privilegios', '15')
    
    if not nombre or not password:
        return jsonify({"error": "Faltan los parámetros 'nombre' y 'password"}), 400
    
    resultados = []
    for ip in diccionario_router_ip.values():
        resultado = agregar_usuario(ip, nombre, password, privilegios)
        resultados.append(resultado)
    
    return jsonify(resultados)

# Ruta para actualizar un usuario en los routers
@app.route('/usuarios/<nombre>', methods=['PUT'])
def actualizar_usuario_api(nombre):
    data = request.get_json()
    password = data.get('password')
    privilegios = data.get('privilegios', '15')
    
    if not password:
        return jsonify({"error": "Falta el parámetro 'password'"}), 400
    
    resultados = []
    for ip in diccionario_router_ip.values():
        resultado = actualizar_usuario(ip, nombre, password, privilegios)
        resultados.append(resultado)
    
    return jsonify(resultados)

# Ruta para eliminar un usuario de los routers
@app.route('/usuarios/<nombre>', methods=['DELETE'])
def eliminar_usuario_api(nombre):
    resultados = []
    for ip in diccionario_router_ip.values():
        resultado = eliminar_usuario(ip, nombre)
        resultados.append(resultado)
    
    return jsonify(resultados)

# Iniciar el servidor
if __name__ == '__main__':
    if primera_ejecucion:
        inicializar_red()  # Llamamos a la función de configuración
        primera_ejecucion = False  # Evitamos que se vuelva a ejecutar
    
    app.run(debug=False)
