import networkx as nx
import matplotlib.pyplot as plt
from gurobipy import *
import random

def get_random_color(used_colors):
    while True:
        color = (random.random(), random.random(), random.random())
        if color not in used_colors:
            return color

def plotter(arcs, node_info, I_total, allowed_routes):
    
    # Create a directed graph
    G = nx.DiGraph()

    # Add nodes to the graph
    G.add_nodes_from(I_total)

    # Add edges to the graph based on arcs
    for arc in arcs:
        i, j, v = arc
        G.add_edge(i, j, vehicle=v)

    # Visualize the graph
    plt.figure(figsize=(10, 6))

    # Define colors for vehicles
    used_colors = set()
    route_colors = {}
    for route in range(allowed_routes):
        color = get_random_color(used_colors)
        used_colors.add(color)
        route_colors[route] = color

    # Draw nodes
    pos = nx.spring_layout(G)  # Layout for better visualization
    nx.draw_networkx_nodes(G, pos, node_size=500, node_color='lightblue')

    # Draw edges for each vehicle with different colors
    for v in range(allowed_routes):
        edges = [(i, j) for i, j, attr in G.edges(data=True) if attr.get('vehicle') == v]
        nx.draw_networkx_edges(G, pos, edgelist=edges, edge_color=route_colors[v], width=2)

    #nx.draw_networkx_labels(G, pos, labels=node_info, font_size=10, font_color='black', font_family='sans-serif', font_weight='normal')

    # Draw labels
    nx.draw_networkx_labels(G, pos)

    # Draw legend for vehicle colors
    for vehicle, color in route_colors.items():
        plt.plot([], [], color=color, label=f'Vehicle {vehicle}')
    plt.legend()

    plt.title("Graph with Arcs for Vehicle Paths")
    plt.axis('off')
    plt.savefig('outputs/graph.jpg', dpi=600, bbox_inches='tight')