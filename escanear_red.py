import json, time, paramiko, pexpect, subprocess

#Debuelve las IP de las interfaces
def escanear_interfaces():
    """Escanea las redes 10.10.10.0/24 y 20.20.30.0/24 y devuelve las IPs de las interfaces en una lista."""
    print("\nEscaneando las redes...\n")
    try:
        # Escanear las dos redes
        redes = ["10.10.10.0/24", "20.20.30.0/24"]
        devices = []

        for red in redes:
            #print(f"Escaneando la red {red}...")
            result = subprocess.run(
                ["nmap", "-sn", red],  # Solo realiza un ping-scan
                capture_output=True,
                text=True
            )
            output = result.stdout

            # Buscar dispositivos en la salida
            for line in output.splitlines():
                if "Nmap scan report for" in line:
                    ip = line.split("for ")[1]
                    devices.append(ip)
        
        # Mostrar resultados
        #print("Dispositivos detectados:")
        #for ip in devices:
        #    print(f"{ip}")
        
        return devices
    
    except Exception as e:
        print(f"Error durante el escaneo: {e}")
        return []

#Obtiene el hostname e una IP
def get_hostname(ip, user="admin", password="admin"):
    try:
        # Inicia la conexión TELNET
        child = pexpect.spawn(f'telnet {ip}', timeout=60)
        child.expect('Username:')
        child.sendline(user)
        child.expect('Password:')
        child.sendline(password)
        
        # Esperar el prompt después de hacer login
        child.expect([r'.+#', r'.+>'])  # Puede ser '#' o '>' dependiendo del dispositivo

        # Capturar el prompt completo
        prompt = child.after.decode('utf-8').strip()  # Usa `after` para capturar el prompt

        # El hostname será todo lo que aparece antes de '#' o '>' y eliminar caracteres
        hostname = prompt.split()[0]  # Se asume que el hostname es la primera palabra
        hostname = hostname.split('#')[0].split('>')[0]

        # Salir de Telnet
        child.sendline("exit")
        
        return hostname

    except Exception as e:
        return f"Error: {str(e)}"

#Obtiene la ip loopback a partir de una ip
def obtener_ip_loopback(host, usuario='admin', contrasena='admin'):
    # Comando de Telnet
    comando_telnet = f"telnet {host}"

    # Iniciar la conexión Telnet
    child = pexpect.spawn(comando_telnet)

    # Esperar a que el prompt de inicio de sesión aparezca
    child.expect('Username:')
    child.sendline(usuario)

    # Esperar a que el prompt de contraseña aparezca
    child.expect('Password:')
    child.sendline(contrasena)

    # Esperar a que aparezca el prompt del router (esto depende del router y su configuración)
    # Aquí puede ser necesario ajustar la espera si el prompt tiene un formato diferente
    child.expect('#')

    # Ejecutar el comando para obtener la IP de la interfaz loopback
    child.sendline('show ip interface brief')  # Comando para obtener información de interfaces

    # Esperar a que aparezca el resultado
    child.expect('#')  # El prompt de fin del comando puede variar

    # Obtener la salida del comando
    output = child.before.decode('utf-8')

    # Buscar la IP de la interfaz Loopback
    for line in output.splitlines():
        if 'Loopback' in line:
            # Suponemos que la IP está en la segunda columna
            ip = line.split()[1]
            return ip

    return None

#Funcion principal
#Obtiene los hostnames e interfaces guardandolas en un json
def obtener_hostnames_y_interfaces():
    # Obtiene las IPs de las interfaces
    interfaces = escanear_interfaces()

    # Diccionario para almacenar los hostnames y sus respectivas interfaces
    network_info = {}

    for ip in interfaces:
        # Obtén el hostname para cada IP
        hostname = get_hostname(ip)

        # Obtén la IP de la interfaz loopback 0
        loopback_ip = obtener_ip_loopback(ip)

        if hostname not in network_info:
            network_info[hostname] = []

        # Agregar las interfaces al diccionario, pero solo si no son la IP de loopback duplicada
        if ip not in network_info[hostname]:
            network_info[hostname].append(ip)

        # Si se obtuvo la IP de loopback y no está ya en la lista, agregarla también
        if loopback_ip and loopback_ip not in network_info[hostname]:
            network_info[hostname].append(loopback_ip)
    
    # Escribir la información en un archivo JSON
    with open("network_info.json", "w") as json_file:
        json.dump(network_info, json_file, indent=4)
    
    print("La información de red se ha guardado en 'network_info.json'.")

def obtener_diccionario_router_ip(file_path="network_info.json"):
    # Leer el archivo JSON
    with open(file_path, 'r') as file:
        json_routers = json.load(file)

    # Creamos un diccionario vacío para almacenar las IPs
    resultado = {}

    # Recorremos cada router en el diccionario
    for router, ips in json_routers.items():
        if ips:  # Aseguramos que la lista de IPs no esté vacía
            resultado[router] = ips[0]  # Guardamos el primer valor de la lista de IPs

    return resultado


# Función que obtiene la información del router a través de SSH
def obtener_informacion_router(hostname, ip):
    try:
        # Crear un cliente SSH
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("paramiko.log")  # Habilitar logs de Paramiko para depuración

        # Conectarse al router
        ssh_client.connect(ip, username="admin", password="admin")

        # Verificar si la conexión está activa
        transport = ssh_client.get_transport()
        if transport is not None and transport.is_active():
            print(f"Conexión SSH establecida exitosamente con {hostname} ({ip}).")
        else:
            print(f"No se pudo establecer la conexión SSH con {hostname} ({ip}).")
            ssh_client.close()
            return None

        # Iniciar una shell interactiva
        shell = ssh_client.invoke_shell()
        time.sleep(1)  # Esperar a que la shell esté lista

        # Configurar el terminal remoto para salida completa
        shell.send('terminal length 0\n')
        time.sleep(1)
        shell.recv(65535)  # Limpiar el buffer inicial

        # Ejecutar el comando 'show version'
        shell.send('show version\n')
        time.sleep(2)  # Dar tiempo al dispositivo para generar la salida
        version_output = shell.recv(65535).decode('utf-8').strip()

        # Ejecutar el comando 'show ip interface brief'
        shell.send('show ip interface brief\n')
        time.sleep(2)
        interfaces_output = shell.recv(65535).decode('utf-8').strip()

        # Procesar la información obtenida
        sistema_operativo = "Desconocido"
        for line in version_output.splitlines():
            if 'Cisco IOS' in line:  # Detectar Cisco IOS en el sistema operativo
                sistema_operativo = line.strip()

        # Buscar la IP de Loopback y obtener interfaces activas con sus IPs
        ip_loopback = None
        interfaces = {}  # Diccionario para almacenar interfaces activas y sus IPs
        for line in interfaces_output.splitlines():
            columns = line.split()
            if len(columns) >= 2:  # Verificar que haya suficientes columnas
                interface_name = columns[0]  # Nombre de la interfaz
                ip_address = columns[1]  # Dirección IP
                status = columns[-2]  # Estado administrativo
                protocol = columns[-1]  # Protocolo

                # Verificar si es Loopback
                if "Loopback" in interface_name:
                    ip_loopback = ip_address

                # Agregar interfaces activas (estado "up")
                if status == "up" and protocol == "up":
                    interfaces[interface_name] = ip_address

        # Simular rol y empresa
        rol = "Router"
        empresa = "Cisco"

        # Cerrar la conexión SSH
        ssh_client.close()

        # Devolver los datos del router en formato de diccionario
        return {
            "nombre": hostname,
            "ip_loopback": ip_loopback,
            "rol": rol,
            "empresa": empresa,
            "sistema_operativo": sistema_operativo,
            "interfaces": interfaces,
            "link_interfaces": "http://127.0.0.1:5000/routers/"+hostname+"/interfaces"
        }

    except paramiko.SSHException as ssh_error:
        print(f"Error SSH con {hostname} ({ip}): {ssh_error}")
    except Exception as e:
        print(f"Error al obtener la información de {hostname} ({ip}): {e}")
    finally:
        try:
            ssh_client.close()
        except:
            pass  # Evitar errores si la conexión ya está cerrada

    return None
