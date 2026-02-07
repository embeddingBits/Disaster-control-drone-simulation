import networkx as nx
from radio import distance, link_capacity_mbps

def build_network(drones, users, base_stations, max_range=300):
    G = nx.Graph()

    for d in drones:
        if d.alive:
            G.add_node(f"D{d.id}", obj=d)

    for u in users:
        G.add_node(f"U{u.id}", obj=u)

    for b in base_stations:
        G.add_node(f"B{b.id}", obj=b)

    nodes = list(G.nodes(data=True))

    for i, (n1, d1) in enumerate(nodes):
        for n2, d2 in nodes[i+1:]:
            p1 = d1["obj"].pos
            p2 = d2["obj"].pos
            d = distance(p1, p2)

            if d <= max_range:
                cap = link_capacity_mbps(d)
                G.add_edge(n1, n2, capacity=cap, distance=d)

    return G

