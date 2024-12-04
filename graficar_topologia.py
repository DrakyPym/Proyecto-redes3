import networkx as nx
import matplotlib.pyplot as plt
import json
import re

# Función para cargar los datos del archivo JSON
def cargar_datos_json():
    with open('network_info.json', 'r') as f:
        return json.load(f)

# Función para identificar si una IP tiene el formato N.N.N.N
def es_ip_loopback(ip):
    # Excluir IPs de la red 10.10.10.X (enlaces troncales)
    if re.match(r'^10\.10\.10\.\d+$', ip):
        return False

    # Verifica si cada octeto de la dirección IP es el mismo
    return bool(re.match(r'^(\d+)\.\1\.\1\.\1$', ip))

# Expresión regular para identificar IPs dentro de la red 10.10.10.X (IPs de enlaces troncales)
def es_ip_troncal(ip):
    return bool(re.match(r"^10\.10\.10\.(\d+)$", ip)) and int(ip.split('.')[3]) % 2 == 1

# Expresión regular para identificar IPs dentro de la red 20.20.30.X
def es_ip_reservada(ip):
    return bool(re.match(r"^20\.20\.30\.\d+$", ip))

# Función para obtener todas las IPs relevantes (10.10.10.X y 20.20.30.X)
def obtener_ips_relevantes(datos):
    ips_relevantes = []

    # Recorrer los nodos y sus respectivas IPs
    for nodo, ips in datos.items():
        for ip in ips:
            if es_ip_troncal(ip) or es_ip_reservada(ip):
                # Agregar la tupla (nodo, ip) en vez de solo la IP
                ips_relevantes.append((nodo, ip))

    return ips_relevantes

# Función para crear el grafo de la topología de la red
def crear_topologia_red(datos):
    G = nx.Graph()
    nodos = {}

    # Recorrer los nodos y sus respectivas IPs
    for nodo, ips in datos.items():
        # Buscar la IP de Loopback entre las IPs del nodo
        loopback_ip = next((ip for ip in ips if es_ip_loopback(ip)), None)

        if loopback_ip:
            # Guardar nodo con su IP de loopback
            nodos[nodo] = loopback_ip
            # Agregar el nodo al grafo con el formato adecuado
            G.add_node(f"{nodo} ({loopback_ip})")

    ips_relevantes = obtener_ips_relevantes(datos)
    aristas = []

    # Crear aristas para las IPs en la red 20.20.30.X
    nodos_20_20_30 = [nodo for nodo, ip in ips_relevantes if es_ip_reservada(ip)]
    for i in range(len(nodos_20_20_30)):
        for j in range(i + 1, len(nodos_20_20_30)):
            aristas.append((nodos_20_20_30[i], nodos_20_20_30[j]))

    # Crear aristas para las IPs en la red 10.10.10.X con números consecutivos en el último octeto
    nodos_10_10_10 = [nodo for nodo, ip in ips_relevantes if es_ip_troncal(ip)]
    
    # Crear un diccionario para almacenar las IPs de la red 10.10.10.X y sus nodos
    ip_to_nodo = {}
    for nodo, ip in ips_relevantes:
        if es_ip_troncal(ip):
            ip_to_nodo[ip] = nodo
    
    # Ordenar las IPs de la red 10.10.10.X por el número final en el último octeto
    ip_ordenadas = sorted(ip_to_nodo.keys(), key=lambda ip: int(ip.split('.')[-1]))

    # Unir nodos con IPs consecutivas en la red 10.10.10.X
    for i in range(len(ip_ordenadas) - 1):
        ip1 = ip_ordenadas[i]
        ip2 = ip_ordenadas[i + 1]
        
        # Verificar si las IPs son consecutivas (último octeto es consecutivo)
        if int(ip2.split('.')[-1]) == int(ip1.split('.')[-1]) + 1:
            aristas.append((ip_to_nodo[ip1], ip_to_nodo[ip2]))
    
    # Traducir las IPs de los nodos a sus nombres (hostnames) antes de agregar las aristas
    aristas_hostnames = []
    for arista in aristas:
        nodo1, nodo2 = arista
        aristas_hostnames.append((nodo1, nodo2))

    # Agregar las aristas al grafo
    for i in range(0, len(aristas_hostnames) - 1, 2):
        G.add_edge(aristas_hostnames[i], aristas_hostnames[i + 1], color='gray', linestyle='-')

    return G

# Cargar los datos dinámicos desde el archivo JSON
datos = cargar_datos_json()

# Crear el grafo con la topología de la red
G = crear_topologia_red(datos)

# Dibujar la topología de la red
plt.figure(figsize=(12, 10))
pos = nx.spring_layout(G, seed=42, k=0.3)  # Ajuste de layout para más claridad
nx.draw(G, pos, with_labels=True, node_size=3000, font_size=12, font_weight='bold', edge_color='gray', node_color='skyblue')

# Mostrar el título
plt.title("Topología de Red entre Routers (Enlaces Troncales)")
plt.show()