import ipaddress
import json
import matplotlib.pyplot as plt
import networkx as nx

# Función para leer el archivo JSON
def leer_json(ruta_archivo):
    with open(ruta_archivo, 'r') as f:
        return json.load(f)

# Función para obtener la red de una IP con máscara /30
def obtener_red(ip):
    ip_obj = ipaddress.IPv4Address(ip)
    # Usar máscara /30
    return ipaddress.IPv4Network(f"{ip_obj}/30", strict=False)

def graficar_enlaces_entre_routers(json_path, output_image_path):
    # Leer el archivo JSON desde el directorio actual
    def leer_json(ruta_archivo):
        with open(ruta_archivo, 'r') as f:
            return json.load(f)

    # Función para obtener la red de una IP con máscara /30
    def obtener_red(ip):
        ip_obj = ipaddress.IPv4Address(ip)
        # Usar máscara /30
        return ipaddress.IPv4Network(f"{ip_obj}/30", strict=False)

    # Crear un grafo para los routers
    G = nx.Graph()

    # Leer el archivo JSON
    routers_json = leer_json(json_path)

    # Recorrer todos los routers y sus IPs para agregar enlaces
    for router, ips in routers_json.items():
        # Agregar el nodo del router al grafo
        G.add_node(router)

    # Compara cada IP con las IPs de todos los demás routers
    for router_a, ips_a in routers_json.items():
        for ip_a in ips_a:
            red_a = obtener_red(ip_a)
            
            # Comparar con todas las IPs de todos los otros routers
            for router_b, ips_b in routers_json.items():
                if router_a != router_b:  # No comparar un router consigo mismo
                    for ip_b in ips_b:
                        red_b = obtener_red(ip_b)
                        
                        # Si las IPs están en la misma red /30, agregar un enlace
                        if red_a == red_b:
                            G.add_edge(router_a, router_b)

    # Graficar el grafo
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, seed=42)  # Layout para distribuir los nodos

    # Dibujar los nodos y los enlaces (aristas)
    nx.draw(
        G, pos, with_labels=True, 
        node_size=3000, node_color="skyblue", 
        font_size=10, font_weight="bold", 
        edge_color="gray", width=2, alpha=0.6
    )

    # Guardar el grafo en un archivo de imagen
    plt.savefig(output_image_path, format="png", dpi=300)
    print(f"Gráfico guardado como {output_image_path}")

    # Opcionalmente, mostrar el grafo
    plt.title("Enlaces entre Routers")
    plt.show()

def obtener_vecinos(hostname, json_path):
    # Leer el archivo JSON
    routers_json = leer_json(json_path)
    
    # Crear un grafo para los routers
    G = nx.Graph()

    # Recorrer todos los routers y sus IPs para agregar enlaces
    for router, ips in routers_json.items():
        # Agregar el nodo del router al grafo
        G.add_node(router)

    # Compara cada IP con las IPs de todos los demás routers
    for router_a, ips_a in routers_json.items():
        for ip_a in ips_a:
            red_a = obtener_red(ip_a)
            
            # Comparar con todas las IPs de todos los otros routers
            for router_b, ips_b in routers_json.items():
                if router_a != router_b:  # No comparar un router consigo mismo
                    for ip_b in ips_b:
                        red_b = obtener_red(ip_b)
                        
                        # Si las IPs están en la misma red /30, agregar un enlace
                        if red_a == red_b:
                            G.add_edge(router_a, router_b)

    # Si el hostname está en el grafo, obtener sus vecinos
    if hostname not in G:
        return f"El router {hostname} no está en el grafo."
    
    # Obtener los vecinos del router
    vecinos = list(G.neighbors(hostname))
    return vecinos


