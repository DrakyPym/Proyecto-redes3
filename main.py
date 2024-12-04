import pexpect
import json
from configuracion_ssh import configure_ssh_from_json
from escanear_red import obtener_hostnames_y_interfaces, obtener_diccionario_router_ip, obtener_informacion_router
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
