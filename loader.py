import pickle
from pyvis.network import Network



def load_graph(filename):


    G = Network()
    with open(filename, 'rb') as gef:
        a = pickle.load(gef)
        # print(a['nodes'])
        # print(a['edges'])
        
        G.nodes = a['nodes']
        G.edges = a['edges']


        # print(G)
        # print(G.nodes)

        id_tracking = a['id_tracking']


    return G, id_tracking




G, id_tracking = load_graph("exported_graph.pkl")


G.barnes_hut(
    gravity=-15000,           # Much stronger repulsion (pushed nodes further apart)
    central_gravity=0.1,      # Lower central pull to allow the graph to expand
    spring_length=400,        # Longer edges to create more "dead space"
    spring_strength=0.005,    # Weaker springs so they don't pull nodes in too tight
    damping=0.9               # High damping to settle the movement quickly
)

G.set_options("""
{
    "nodes": {
        "font" : {
            "face" : "arial",
            "size" : 6
        },
        "size": 4,
        "borderWidth": 1,
        "color": {
        "background": "#82b1ff",
        "border": "#4e83d1"
        }
    },
    "edges": {
        "smooth": false,
        "width": 1,
        "color": {
        "color": "#4e83d1",
        "opacity": 0.3
        }
    }
}
""")


# print(G)
G.show("a.html",notebook=False)