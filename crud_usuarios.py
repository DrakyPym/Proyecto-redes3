import paramiko
import time
import json

def obtener_usuarios_router(hostname, ip):
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

        # Ejecutar el comando 'show running-config' para obtener información de usuarios
        shell.send('show running-config\n')
        time.sleep(3)  # Dar tiempo al dispositivo para generar la salida
        running_config_output = shell.recv(65535).decode('utf-8').strip()

        # Procesar la información de los usuarios
        usuarios = []
        for line in running_config_output.splitlines():
            if 'username' in line:  # Buscar líneas que contengan información de usuarios
                # Extraer el nombre de usuario y los permisos (si los tiene)
                columns = line.split()
                if len(columns) >= 3:
                    usuario = columns[1]  # Nombre del usuario
                    permisos = columns[2] if len(columns) > 2 else "Ninguno"  # Permisos (si están definidos)
                    # Agregar solo el nombre de usuario y el nivel de privilegio, sin la contraseña
                    privilegio = columns[3] if len(columns) > 3 else "Desconocido"
                    usuarios.append({
                        "usuario": usuario,
                        "permisos": permisos,
                        "privilegio": privilegio
                    })

        # Cerrar la conexión SSH
        ssh_client.close()

        # Devolver los datos del router en formato JSON
        return json.dumps({
            "nombre": hostname,
            "ip": ip,
            "usuarios": usuarios
        }, indent=4)

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


def agregar_usuario_en_router(hostname, ip, nombre_usuario, contrasena, privilegio):
    try:
        # Crear un cliente SSH
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Conectarse al router
        ssh_client.connect(ip, username="admin", password="admin")

        # Iniciar una shell interactiva
        shell = ssh_client.invoke_shell()
        time.sleep(1)

        # Configurar el terminal remoto para salida completa
        shell.send('terminal length 0\n')
        time.sleep(1)
        shell.recv(65535)  # Limpiar el buffer inicial

        # Comando para agregar un nuevo usuario con el nivel de privilegio proporcionado
        shell.send(f'conf t\n')
        time.sleep(1)
        shell.recv(65535)
        
        # Agregar el nuevo usuario con el privilegio especificado
        shell.send(f'username {nombre_usuario} privilege {privilegio} secret {contrasena}\n')
        time.sleep(2)
        
        # Verificar que el usuario haya sido agregado
        shell.send('show running-config | include username\n')
        time.sleep(2)
        output = shell.recv(65535).decode('utf-8').strip()

        # Procesar la salida para verificar que el usuario ha sido agregado
        for line in output.splitlines():
            if nombre_usuario in line:
                # Extraer los permisos
                columnas = line.split()
                permisos = columnas[2] if len(columnas) > 2 else "Ninguno"
                # Devolver la información del usuario agregado
                return {
                    "usuario": nombre_usuario,
                    "permisos": permisos
                }

        # Si no se encuentra el usuario en la salida, retornar None
        return None
    except Exception as e:
        print(f"Error al agregar el usuario: {e}")
    finally:
        # Asegurarse de cerrar la conexión SSH
        ssh_client.close()

    return None

