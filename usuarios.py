from netmiko import ConnectHandler, NetmikoTimeoutException, NetMikoAuthenticationException

# Función para leer los usuarios con permisos
def leer_usuarios_con_permisos(router_ip):
    dispositivo = {
        'device_type': 'cisco_ios',  # Usamos SSH
        'ip': router_ip,
        'username': 'admin',
        'password': 'admin',
    }

    try:
        # Conectar al router
        conexion = ConnectHandler(**dispositivo)
        
        # Ejecutar comando para obtener los usuarios configurados
        usuarios_output = conexion.send_command('show running-config | include username')
        
        # Desconectar
        conexion.disconnect()

        # Procesar la salida para extraer los usuarios
        usuarios = []
        for line in usuarios_output.splitlines():
            if "username" in line:
                parts = line.split()
                nombre = parts[1]  # El nombre de usuario está en la segunda columna
                privilegios = parts[3] if len(parts) > 3 else 'N/A'  # Los privilegios suelen estar en la cuarta columna
                usuarios.append({"nombre": nombre, "privilegios": privilegios, "router": router_ip})

        return usuarios

    except Exception as e:
        return [{"error": f"Error al conectarse a {router_ip}: {str(e)}"}]

