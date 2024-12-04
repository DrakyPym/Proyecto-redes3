import paramiko
import json
import os

# Datos de conexión SSH
hostname = '192.168.1.1'
port = 22
username = 'your_username'
password = 'your_password'

# Función para crear una conexión SSH
def crear_conexion():
    try:
        cliente = paramiko.SSHClient()
        cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cliente.connect(hostname, port=port, username=username, password=password)
        return cliente
    except Exception as e:
        print(f"Error al conectar: {e}")
        return None

# Función para ejecutar un comando remoto a través de SSH
def ejecutar_comando(cliente, comando):
    try:
        stdin, stdout, stderr = cliente.exec_command(comando)
        salida = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        if error:
            print(f"Error: {error}")
        return salida
    except Exception as e:
        print(f"Error al ejecutar el comando: {e}")
        return None

# Ruta relativa para el archivo de usuarios en el repositorio
ruta_archivo_json = 'network_info.json'

# Función para recuperar los usuarios del router
def obtener_usuarios(cliente):
    try:
        # Comando que lee el archivo JSON de usuarios en el router
        comando = f"cat {ruta_archivo_json}"
        salida = ejecutar_comando(cliente, comando)
        if salida:
            return json.loads(salida)
        else:
            return []
    except Exception as e:
        print(f"Error al obtener los usuarios: {e}")
        return []

# Función para agregar un nuevo usuario al router
def agregar_usuario(cliente, usuario):
    try:
        usuarios = obtener_usuarios(cliente)  # Obtenemos los usuarios existentes
        usuarios.append(usuario)  # Agregamos el nuevo usuario
        archivo_json = json.dumps(usuarios, indent=2)
        comando = f"echo '{archivo_json}' > {ruta_archivo_json}"
        ejecutar_comando(cliente, comando)
        return usuario
    except Exception as e:
        print(f"Error al agregar el usuario: {e}")
        return None

# Función para actualizar un usuario en el router
def actualizar_usuario(cliente, usuario_id, nuevo_usuario):
    try:
        usuarios = obtener_usuarios(cliente)  # Obtenemos los usuarios existentes
        for i, usuario in enumerate(usuarios):
            if usuario['id'] == usuario_id:
                usuarios[i] = nuevo_usuario  # Actualizamos el usuario
                archivo_json = json.dumps(usuarios, indent=2)
                comando = f"echo '{archivo_json}' > {ruta_archivo_json}"
                ejecutar_comando(cliente, comando)
                return nuevo_usuario
        print(f"Usuario con id {usuario_id} no encontrado.")
        return None
    except Exception as e:
        print(f"Error al actualizar el usuario: {e}")
        return None

# Función para eliminar un usuario en todos los routers
def eliminar_usuario(cliente, usuario_id):
    try:
        usuarios = obtener_usuarios(cliente)  # Obtenemos los usuarios existentes
        usuario_eliminado = None
        for i, usuario in enumerate(usuarios):
            if usuario['id'] == usuario_id:
                usuario_eliminado = usuarios.pop(i)  # Eliminamos el usuario
                break
        if usuario_eliminado:
            archivo_json = json.dumps(usuarios, indent=2)
            comando = f"echo '{archivo_json}' > {ruta_archivo_json}"
            ejecutar_comando(cliente, comando)
            return usuario_eliminado
        else:
            print(f"Usuario con id {usuario_id} no encontrado.")
            return None
    except Exception as e:
        print(f"Error al eliminar el usuario: {e}")
        return None