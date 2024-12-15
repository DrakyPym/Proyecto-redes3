import json
import ipaddress
import matplotlib.pyplot as plt
import networkx as nx
import threading
import time
import paramiko
from escanear_red import obtener_hostnames_y_interfaces, obtener_diccionario_router_ip, obtener_informacion_router, obtener_informacion_interfaces
from flask import Flask, jsonify, request
from graficacion import graficar_enlaces_entre_routers, obtener_vecinos
from configuracion_ssh import configure_ssh_from_json
from usuarios import leer_usuarios_con_permisos
from crud_usuarios import obtener_usuarios_router, agregar_usuario_en_router

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

# Ruta para obtener los usuarios de todos los routers
@app.route('/usuarios', methods=['GET'])
def obtener_usuarios():
    usuarios = []
    for ip in diccionario_router_ip.values():
        usuarios_router = leer_usuarios_con_permisos(ip)
        if usuarios_router:
            usuarios.extend(usuarios_router)
    return jsonify(usuarios)

@app.route('/usuarios', methods=['POST'])
def agregar_usuario_a_todos_los_routers():
    # Obtener los datos de la solicitud POST
    data = request.get_json()
    usuario = data.get('usuario')
    contrasena = data.get('contrasena')
    privilegio = data.get('privilegio')

    # Validar que los parámetros 'usuario', 'contrasena', y 'privilegio' estén presentes
    if not usuario or not contrasena or not privilegio:
        return jsonify({"error": "Faltan parámetros: 'usuario', 'contrasena', o 'privilegio'"}), 400

    usuarios_actualizados = {}

    for hostname, ip in diccionario_router_ip.items():
        try:
            # Crear un cliente SSH
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            paramiko.util.log_to_file("paramiko.log")  # Habilitar logs de Paramiko para depuración

            # Conectarse al router
            ssh_client.connect(ip, username="admin", password="admin")

            # Iniciar una shell interactiva
            shell = ssh_client.invoke_shell()
            time.sleep(1)  # Esperar a que la shell esté lista

            # Configurar el terminal remoto para salida completa
            shell.send('terminal length 0\n')
            time.sleep(1)
            shell.recv(65535)  # Limpiar el buffer inicial

            # Enviar comando para agregar el nuevo usuario
            shell.send(f'conf t\nusername {usuario} privilege {privilegio} secret {contrasena}\n')
            time.sleep(2)
            shell.send('end\n')
            time.sleep(1)

            # Ejecutar 'show running-config' para verificar los cambios
            shell.send('show running-config\n')
            time.sleep(3)
            running_config_output = shell.recv(65535).decode('utf-8').strip()

            # Procesar la información de los usuarios
            usuarios = []
            for line in running_config_output.splitlines():
                if 'username' in line:  # Buscar líneas que contengan información de usuarios
                    columns = line.split()
                    if len(columns) >= 3:
                        usuario = columns[1]  # Nombre del usuario
                        permisos = columns[2] if len(columns) > 2 else "Ninguno"  # Permisos (si están definidos)
                        privilegio = columns[3] if len(columns) > 3 else "Desconocido"
                        usuarios.append({
                            "usuario": usuario,
                            "permisos": permisos,
                            "privilegio": privilegio
                        })

            # Cerrar la conexión SSH
            ssh_client.close()

            # Guardar la lista de usuarios actualizados por router
            usuarios_actualizados[hostname] = {
                "ip": ip,
                "usuarios": usuarios
            }

        except paramiko.SSHException as ssh_error:
            print(f"Error SSH con {hostname} ({ip}): {ssh_error}")
            usuarios_actualizados[hostname] = {
                "error": f"Error SSH con {hostname} ({ip}): {ssh_error}"
            }
        except Exception as e:
            print(f"Error al agregar el usuario en {hostname} ({ip}): {e}")
            usuarios_actualizados[hostname] = {
                "error": f"Error al agregar el usuario en {hostname} ({ip}): {e}"
            }

    # Devolver la información actualizada de todos los routers
    return jsonify(usuarios_actualizados)


@app.route('/usuarios', methods=['PUT'])
def actualizar_usuario_en_todos_los_routers():
    # Obtener los datos de la solicitud PUT
    data = request.get_json()
    usuario = data.get('usuario')
    nueva_contrasena = data.get('nueva_contrasena')
    nuevo_privilegio = data.get('nuevo_privilegio')

    # Validar que los parámetros 'usuario', 'nueva_contrasena', y 'nuevo_privilegio' estén presentes
    if not usuario or not nueva_contrasena or not nuevo_privilegio:
        return jsonify({"error": "Faltan parámetros: 'usuario', 'nueva_contrasena', o 'nuevo_privilegio'"}), 400

    usuarios_actualizados = {}

    for hostname, ip in diccionario_router_ip.items():
        try:
            # Crear un cliente SSH
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            paramiko.util.log_to_file("paramiko.log")  # Habilitar logs de Paramiko para depuración

            # Conectarse al router
            ssh_client.connect(ip, username="admin", password="admin")

            # Iniciar una shell interactiva
            shell = ssh_client.invoke_shell()
            time.sleep(1)  # Esperar a que la shell esté lista

            # Configurar el terminal remoto para salida completa
            shell.send('terminal length 0\n')
            time.sleep(1)
            shell.recv(65535)  # Limpiar el buffer inicial

            # Enviar comando para actualizar la contraseña y privilegio del usuario
            shell.send(f'conf t\nusername {usuario} privilege {nuevo_privilegio} secret {nueva_contrasena}\n')
            time.sleep(2)
            shell.send('end\n')
            time.sleep(1)

            # Ejecutar 'show running-config' para verificar los cambios
            shell.send('show running-config\n')
            time.sleep(3)
            running_config_output = shell.recv(65535).decode('utf-8').strip()

            # Procesar la información de los usuarios
            usuarios = []
            for line in running_config_output.splitlines():
                if 'username' in line:  # Buscar líneas que contengan información de usuarios
                    columns = line.split()
                    if len(columns) >= 3:
                        usuario = columns[1]  # Nombre del usuario
                        permisos = columns[2] if len(columns) > 2 else "Ninguno"  # Permisos (si están definidos)
                        privilegio = columns[3] if len(columns) > 3 else "Desconocido"
                        usuarios.append({
                            "usuario": usuario,
                            "permisos": permisos,
                            "privilegio": privilegio
                        })

            # Cerrar la conexión SSH
            ssh_client.close()

            # Guardar la lista de usuarios actualizados por router
            usuarios_actualizados[hostname] = {
                "ip": ip,
                "usuarios": usuarios
            }

        except paramiko.SSHException as ssh_error:
            print(f"Error SSH con {hostname} ({ip}): {ssh_error}")
            usuarios_actualizados[hostname] = {
                "error": f"Error SSH con {hostname} ({ip}): {ssh_error}"
            }
        except Exception as e:
            print(f"Error al actualizar el usuario en {hostname} ({ip}): {e}")
            usuarios_actualizados[hostname] = {
                "error": f"Error al actualizar el usuario en {hostname} ({ip}): {e}"
            }

    # Devolver la información actualizada de todos los routers
    return jsonify(usuarios_actualizados)

@app.route('/usuarios', methods=['DELETE'])
def eliminar_usuario_en_todos_los_routers():
    # Obtener los datos de la solicitud DELETE
    data = request.get_json()
    usuario = data.get('usuario')

    # Validar que el parámetro 'usuario' esté presente
    if not usuario:
        return jsonify({"error": "Falta el parámetro 'usuario'"}), 400

    usuarios_eliminados = {}

    for hostname, ip in diccionario_router_ip.items():
        try:
            # Crear un cliente SSH
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            paramiko.util.log_to_file("paramiko.log")  # Habilitar logs de Paramiko para depuración

            # Conectarse al router
            ssh_client.connect(ip, username="admin", password="admin")

            # Iniciar una shell interactiva
            shell = ssh_client.invoke_shell()
            time.sleep(1)  # Esperar a que la shell esté lista

            # Configurar el terminal remoto para salida completa
            shell.send('terminal length 0\n')
            time.sleep(1)
            shell.recv(65535)  # Limpiar el buffer inicial

            # Enviar comando para eliminar el usuario
            shell.send(f'conf t\nno username {usuario}\n')
            time.sleep(2)
            shell.send('end\n')
            time.sleep(1)

            # Ejecutar 'show running-config' para verificar los cambios
            shell.send('show running-config\n')
            time.sleep(3)
            running_config_output = shell.recv(65535).decode('utf-8').strip()

            # Procesar la información de los usuarios después de la eliminación
            usuarios = []
            for line in running_config_output.splitlines():
                if 'username' in line:  # Buscar líneas que contengan información de usuarios
                    columns = line.split()
                    if len(columns) >= 3:
                        usuario = columns[1]  # Nombre del usuario
                        permisos = columns[2] if len(columns) > 2 else "Ninguno"  # Permisos (si están definidos)
                        privilegio = columns[3] if len(columns) > 3 else "Desconocido"
                        usuarios.append({
                            "usuario": usuario,
                            "permisos": permisos,
                            "privilegio": privilegio
                        })

            # Cerrar la conexión SSH
            ssh_client.close()

            # Guardar la lista de usuarios actualizados por router
            usuarios_eliminados[hostname] = {
                "ip": ip,
                "usuarios": usuarios
            }

        except paramiko.SSHException as ssh_error:
            print(f"Error SSH con {hostname} ({ip}): {ssh_error}")
            usuarios_eliminados[hostname] = {
                "error": f"Error SSH con {hostname} ({ip}): {ssh_error}"
            }
        except Exception as e:
            print(f"Error al eliminar el usuario en {hostname} ({ip}): {e}")
            usuarios_eliminados[hostname] = {
                "error": f"Error al eliminar el usuario en {hostname} ({ip}): {e}"
            }

    # Devolver la información actualizada de todos los routers
    return jsonify(usuarios_eliminados)


@app.route('/routers/<hostname>/usuarios/', methods=['GET'])
def obtener_usuarios_por_router(hostname):
    if hostname in diccionario_router_ip:
        usuarios = obtener_usuarios_router(hostname, diccionario_router_ip[hostname])
        return usuarios, 200 
    else:
        return jsonify({"error 404": "No se pudo obtener la informacion del router"}), 404
    
@app.route('/routers/<hostname>/usuarios/', methods=['POST'])
def agregar_usuario_router(hostname):
    try:
        # Obtener la IP del router desde el diccionario
        ip_router = diccionario_router_ip.get(hostname)
        if not ip_router:
            return jsonify({"error": "Router no encontrado"}), 404
        
        # Obtener datos del cuerpo de la solicitud (nuevo usuario)
        data = request.get_json()
        if not data or "usuario" not in data or "contrasena" not in data or "privilegio" not in data:
            return jsonify({"error": "Datos incompletos. Se requiere 'usuario', 'contrasena' y 'privilegio'"}), 400
        
        # Extraer los datos
        nombre_usuario = data["usuario"]
        contrasena = data["contrasena"]
        privilegio = data["privilegio"]

        # Validar el nivel de privilegio (debe estar entre 0 y 15)
        if privilegio < 0 or privilegio > 15:
            return jsonify({"error": "El nivel de privilegio debe estar entre 0 y 15"}), 400

        # Conectar al router y agregar el usuario
        resultado = agregar_usuario_en_router(hostname, ip_router, nombre_usuario, contrasena, privilegio)

        if resultado:
            # Si el usuario fue agregado correctamente, devolver la información del nuevo usuario
            return jsonify(resultado), 201
        else:
            return jsonify({"error": "No se pudo agregar el usuario al router"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/routers/<hostname>/usuarios/', methods=['PUT'])
def actualizar_usuario_router(hostname):
    # Obtener los datos de la solicitud PUT
    data = request.get_json()
    usuario = data.get('usuario')
    contrasena = data.get('contrasena')
    privilegio = data.get('privilegio')

    # Validar que los parámetros requeridos estén presentes
    if not usuario or not contrasena or not privilegio:
        return jsonify({"error": "Faltan parámetros: usuario, contrasena, privilegio"}), 400

    # Obtener la IP del router desde un diccionario (debes definir este diccionario)
    ip = diccionario_router_ip.get(hostname)
    if not ip:
        return jsonify({"error": f"Router con hostname {hostname} no encontrado"}), 404

    try:
        # Crear un cliente SSH
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("paramiko.log")  # Habilitar logs de Paramiko para depuración

        # Conectarse al router
        ssh_client.connect(ip, username="admin", password="admin")

        # Iniciar una shell interactiva
        shell = ssh_client.invoke_shell()
        time.sleep(1)  # Esperar a que la shell esté lista

        # Configurar el terminal remoto para salida completa
        shell.send('terminal length 0\n')
        time.sleep(1)
        shell.recv(65535)  # Limpiar el buffer inicial

        # Enviar comando para agregar o actualizar el usuario en el router
        shell.send(f'conf t\nusername {usuario} privilege {privilegio} secret {contrasena}\n')
        time.sleep(2)
        shell.send('end\n')
        time.sleep(1)

        # Ejecutar 'show running-config' para verificar los cambios
        shell.send('show running-config\n')
        time.sleep(3)
        running_config_output = shell.recv(65535).decode('utf-8').strip()

        # Procesar la información de los usuarios
        usuarios = []
        for line in running_config_output.splitlines():
            if 'username' in line:  # Buscar líneas que contengan información de usuarios
                columns = line.split()
                if len(columns) >= 3:
                    usuario = columns[1]  # Nombre del usuario
                    permisos = columns[2] if len(columns) > 2 else "Ninguno"  # Permisos (si están definidos)
                    privilegio = columns[3] if len(columns) > 3 else "Desconocido"
                    usuarios.append({
                        "usuario": usuario,
                        "permisos": permisos,
                        "privilegio": privilegio
                    })

        # Cerrar la conexión SSH
        ssh_client.close()

        # Devolver los datos del router con el usuario actualizado en formato JSON
        return jsonify({
            "nombre": hostname,
            "ip": ip,
            "usuarios": usuarios
        })

    except paramiko.SSHException as ssh_error:
        print(f"Error SSH con {hostname} ({ip}): {ssh_error}")
        return jsonify({"error": f"Error SSH con {hostname} ({ip}): {ssh_error}"}), 500
    except Exception as e:
        print(f"Error al actualizar el usuario en {hostname} ({ip}): {e}")
        return jsonify({"error": f"Error al actualizar el usuario en {hostname} ({ip}): {e}"}), 500
    finally:
        try:
            ssh_client.close()
        except:
            pass  # Evitar errores si la conexión ya está cerrada

@app.route('/routers/<hostname>/usuarios/', methods=['DELETE'])
def eliminar_usuario_router(hostname):
    # Obtener los datos de la solicitud DELETE (en este caso, el usuario que se quiere eliminar)
    data = request.get_json()
    usuario_a_eliminar = data.get('usuario')

    # Validar que el parámetro 'usuario' esté presente
    if not usuario_a_eliminar:
        return jsonify({"error": "Falta el parámetro 'usuario'"}), 400

    # Obtener la IP del router desde un diccionario (debes definir este diccionario)
    ip = diccionario_router_ip.get(hostname)
    if not ip:
        return jsonify({"error": f"Router con hostname {hostname} no encontrado"}), 404

    try:
        # Crear un cliente SSH
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("paramiko.log")  # Habilitar logs de Paramiko para depuración

        # Conectarse al router
        ssh_client.connect(ip, username="admin", password="admin")

        # Iniciar una shell interactiva
        shell = ssh_client.invoke_shell()
        time.sleep(1)  # Esperar a que la shell esté lista

        # Configurar el terminal remoto para salida completa
        shell.send('terminal length 0\n')
        time.sleep(1)
        shell.recv(65535)  # Limpiar el buffer inicial

        # Enviar comando para eliminar el usuario
        shell.send(f'conf t\nno username {usuario_a_eliminar}\n')
        time.sleep(2)
        shell.send('end\n')
        time.sleep(1)

        # Ejecutar 'show running-config' para verificar los cambios
        shell.send('show running-config\n')
        time.sleep(3)
        running_config_output = shell.recv(65535).decode('utf-8').strip()

        # Procesar la información de los usuarios
        usuarios = []
        for line in running_config_output.splitlines():
            if 'username' in line:  # Buscar líneas que contengan información de usuarios
                columns = line.split()
                if len(columns) >= 3:
                    usuario = columns[1]  # Nombre del usuario
                    permisos = columns[2] if len(columns) > 2 else "Ninguno"  # Permisos (si están definidos)
                    privilegio = columns[3] if len(columns) > 3 else "Desconocido"
                    usuarios.append({
                        "usuario": usuario,
                        "permisos": permisos,
                        "privilegio": privilegio
                    })

        # Cerrar la conexión SSH
        ssh_client.close()

        # Devolver los datos del router con la lista de usuarios actualizada en formato JSON
        return jsonify({
            "nombre": hostname,
            "ip": ip,
            "usuarios": usuarios
        })

    except paramiko.SSHException as ssh_error:
        print(f"Error SSH con {hostname} ({ip}): {ssh_error}")
        return jsonify({"error": f"Error SSH con {hostname} ({ip}): {ssh_error}"}), 500
    except Exception as e:
        print(f"Error al eliminar el usuario en {hostname} ({ip}): {e}")
        return jsonify({"error": f"Error al eliminar el usuario en {hostname} ({ip}): {e}"}), 500
    finally:
        try:
            ssh_client.close()
        except:
            pass  # Evitar errores si la conexión ya está cerrada



# Iniciar el servidor
if __name__ == '__main__':
    if primera_ejecucion:
        inicializar_red()  # Llamamos a la función de configuración
        primera_ejecucion = False  # Evitamos que se vuelva a ejecutar
    
    app.run(debug=False)
