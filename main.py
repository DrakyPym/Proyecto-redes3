import json
from configuracion_ssh import configure_ssh_from_json
from escanear_red import obtener_diccionario_router_ip, obtener_informacion_router, obtener_informacion_interfaces
from flask import Flask, jsonify, request

# Variables globales
diccionario_router_ip = {}
primera_ejecucion = True

app = Flask(__name__)

# Función que ejecuta la configuración SSH y escanea la red
def inicializar_red():
    print("Configurando SSH y escaneando la red")
    #Descomentar al terminar
    #configure_ssh_from_json()
    global diccionario_router_ip
    diccionario_router_ip = obtener_diccionario_router_ip()

@app.route('/topologia/grafica', methods=['GET'])
def graficarTopologia():
    return jsonify({"message": "Hello, World!"})

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
        
        # Devolver la información obtenida en formato JSON
        return jsonify(json.loads(resultado)), 200
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
