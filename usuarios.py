from netmiko import ConnectHandler, NetmikoTimeoutException, NetMikoAuthenticationException


# Función para agregar un usuario
def agregar_usuario(router_ip, nombre, password, privilegios='15'):
    dispositivo = {
        'device_type': 'cisco_ios',  # Usamos SSH para conectar
        'ip': router_ip,
        'username': 'admin',
        'password': 'admin',
    }

    try:
        # Conectar al router
        conexion = ConnectHandler(**dispositivo)
        
        # Crear el comando para agregar el usuario
        comando = f"username {nombre} privilege {privilegios} secret {password}"
        
        # Enviar el comando al router
        conexion.send_config_set([comando])
        
        # Guardar la configuración
        conexion.save_config()
        
        # Desconectar
        conexion.disconnect()
        
        return {"status": "completado", "descripcion": f"Usuario {nombre} agregado en {router_ip}"}
    
    except (NetmikoTimeoutException, AuthenticationException) as e:
        return {"status": "error", "descripcion": f"Error de conexión o autenticación: {str(e)}"}
    
    except Exception as e:
        return {"status": "error", "descripcion": f"Error inesperado: {str(e)}"}

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

# Función para actualizar un usuario
def actualizar_usuario(router_ip, nombre, password, privilegios='15'):
    dispositivo = {
        'device_type': 'cisco_ios',  # Usamos SSH
        'ip': router_ip,
        'username': 'admin',
        'password': 'admin',
    }

    try:
        # Conectar al router
        conexion = ConnectHandler(**dispositivo)
        
        # Crear el comando para actualizar el usuario
        comando = f"username {nombre} privilege {privilegios} secret {password}"
        
        # Enviar el comando al router
        conexion.send_config_set([comando])
        
        # Guardar la configuración
        conexion.save_config()
        
        # Desconectar
        conexion.disconnect()
        
        return {"status": "completado", "descripcion": f"Usuario {nombre} actualizado en {router_ip}"}
    
    except (NetmikoTimeoutException, AuthenticationException) as e:
        return {"status": "error", "descripcion": f"Error de conexión o autenticación: {str(e)}"}
    
    except Exception as e:
        return {"status": "error", "descripcion": f"Error inesperado: {str(e)}"}

# Función para eliminar un usuario
def eliminar_usuario(router_ip, nombre):
    dispositivo = {
        'device_type': 'cisco_ios',  # Usamos SSH
        'ip': router_ip,
        'username': 'admin',
        'password': 'admin',
    }

    try:
        # Conectar al router
        conexion = ConnectHandler(**dispositivo)
        
        # Crear el comando para eliminar el usuario
        comando = f"no username {nombre}"
        
        # Enviar el comando al router
        conexion.send_config_set([comando])
        
        # Guardar la configuración
        conexion.save_config()
        
        # Desconectar
        conexion.disconnect()
        
        return {"status": "completado", "descripcion": f"Usuario {nombre} eliminado en {router_ip}"}
    
    except (NetmikoTimeoutException, AuthenticationException) as e:
        return {"status": "error", "descripcion": f"Error de conexión o autenticación: {str(e)}"}
    
    except Exception as e:
        return {"status": "error", "descripcion": f"Error inesperado: {str(e)}"}

