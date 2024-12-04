import subprocess
import pexpect
import json

#Debuelve las IP de las interfaces
def escanear_interfaces():
    """Escanea las redes 10.10.10.0/24 y 20.20.30.0/24 y devuelve las IPs de las interfaces en una lista."""
    print("Iniciando escaneo de redes...")
    try:
        # Escanear las dos redes
        redes = ["10.10.10.0/24", "20.20.30.0/24"]
        devices = []

        for red in redes:
            print(f"Escaneando la red {red}...")
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
        print("Dispositivos detectados:")
        for ip in devices:
            print(f"{ip}")
        
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

