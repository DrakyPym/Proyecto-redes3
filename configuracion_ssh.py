import pexpect
import json
from escanear_red import obtener_hostnames_y_interfaces

# Función para configurar SSH en un router
def configure_ssh(hostname, ip, user="admin", password="admin"):
    try:
        # Inicia la conexión Telnet
        print(f"Conectando a {ip} para configurar SSH...")
        child = pexpect.spawn(f'telnet {ip}', timeout=60)
        child.expect('Username:')
        child.sendline(user)
        child.expect('Password:')
        child.sendline(password)
        child.expect(f'{hostname}#')

        # Comandos para configurar SSH
        comandos = [
            "configure terminal",
            "ip domain-name adminredes.escom.ipn",  # Cambia el dominio a algo adecuado
            "ip ssh rsa keypair-name sshkey",
            "crypto key generate rsa usage-keys label sshkey modulus 2048",  # 2048 bits por seguridad
            "ip ssh v 2",
            "ip ssh time-out 30",
            "ip ssh authentication-retries 3",
            "line vty 0 15",
            "transport input ssh telnet",
            "end"
        ]

        for cmd in comandos:
            child.sendline(cmd)
            if "crypto key generate rsa" in cmd:
                child.expect(['El nombre de las claves sera:', r'.+#'])
                child.sendline("")  # Usa valor predeterminado
                child.expect(['Realmente deseas reemplazarlas?', r'.+#'])
                child.sendline("yes")  # Responde "sí"

            child.expect(r'.+#')  # Espera cualquier prompt del router

        # Salir de Telnet
        child.sendline("exit")
        return {"status": "completado", "descripcion": f"SSH configurado en {hostname} ({ip})"}
    except pexpect.TIMEOUT:
        return {"status": "fallo", "error": f"Timeout al conectar con {ip}"}
    except pexpect.EOF:
        return {"status": "fallo", "error": f"Fin inesperado al conectar con {ip}"}
    except Exception as e:
        return {"status": "fallo", "error": str(e)}

# Función principal
# Función para configurar SSH en todos los routers a partir de un archivo JSON
def configure_ssh_from_json(json_file="network_info.json", user="admin", password="admin"):
    obtener_hostnames_y_interfaces()
    # Cargar el archivo JSON con las IPs de los routers
    with open(json_file, "r") as file:
        data = json.load(file)

    results = {}
    for hostname, ips in data.items():
        # Filtrar la IP loopback (x.x.x.x donde todos los octetos son iguales)
        loopback_ip = next((ip for ip in ips if len(set(ip.split("."))) == 1), None)

        if loopback_ip:
            print(f"Configurando SSH en {hostname} con IP loopback {loopback_ip}")
            result = configure_ssh(hostname, loopback_ip, user, password)
            results[hostname] = result
        else:
            print(f"No se encontró IP loopback para {hostname}")
            results[hostname] = {"status": "fallo", "descripcion": "No se encontró IP loopback"}

    print("Resultados de la configuración SSH:")
    for hostname, result in results.items():
        print(f"{hostname}: {result}")
