import requests

from pyvis.network import Network
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urlparse




def check_url_type(url):
    print(url)
    parsed = urlparse(url)
    # print(parsed.scheme, parsed.netloc, parsed.path)

    if parsed.scheme in ['http', 'https']:
        return "full"
    if parsed.netloc != "" or url.startswith("//"):
        # print("hostname", url)
        return "hostname"
    if url.startswith('/'):
        return "path"

    return "unknown"


def req_get(url):
    ua = UserAgent()
    headers = {'User-Agent': ua.chrome} 
    response = requests.get(url, headers=headers)

    return response.text

def get_all_links(n,html,url):
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    soup = BeautifulSoup(html, 'html.parser')

    # 2. Target the specific Wikipedia content container
    # 'mw-content-text' is usually the most reliable for the article body
    soup = soup.find("div", id="mw-content-text")

    if not soup:
        return []
    # title = soup.title.string

    all_links = []
    count = 0

    for a_tag in soup.find_all("a"):
        if type(n) == type('s'):
            pass
        elif type(n) == type(1000):
            if count >= n:
                break

        

        get_href = a_tag.get('href')

        internal_namespaces = ('File:', 'Category:', 'Help:', 'Special:', 'Template:', 'Talk:', 'Portal:')

        url_type = check_url_type(get_href)
        # print(get_href)
        if get_href == None or type(get_href) != type('str') or get_href[0] == '#' :
            continue
        if "/wiki/" not in get_href:
            continue
        if any(i in get_href for i in internal_namespaces):
            continue

        if url_type == "full":
            to_append = get_href.split("?")[0]
        elif url_type == "hostname":
            to_append = f"{parsed.scheme}:{get_href}"
        else: 
            to_append = f"{base_url}{get_href.split("?")[0]}"

        all_links.append(to_append)
        count += 1


    # for link in soup.find_all("a")[0:3]:
    #     data = link.get('href')
        
    return all_links


def create_and_connect_graph(G, label, url, connect_to):
    new_id = len(G.nodes)+1
    G.add_node(new_id, label=label, url=url)

    G.add_edge(new_id, connect_to)


    return new_id



def export_graph(id_tracking, edges, nodes, filename):
    import pickle

    to_save = {
        "id_tracking": id_tracking,
        "edges" : edges,
        "nodes" : nodes
    }

    with open(filename, 'wb') as gef:
        a = pickle.dump(to_save,gef)


    print("exported_graph")




if __name__ == '__main__':

    url_extraction_count = 15
    max_depth = 50
    do_export_graph = True

    # load_graph = False

    id_tracking = {}
    root_url = 'https://en.wikipedia.org/wiki/Indonesia'
    
    G = Network('80vh', '80vw')

    # if load_graph:
    #     import pickle

    #     pickle.load()


    root_node_id = 1
    G.add_node(root_node_id, label=root_url, url=root_url)
    id_tracking[root_url] = root_node_id

    root_link_list = get_all_links(url_extraction_count, req_get(root_url), root_url)
    for crawled_link in root_link_list:
        crawled_link = crawled_link.rstrip('/')

            # existing_id = id_tracking.get(crawled_link, None)
        if crawled_link in id_tracking:
            G.add_edge(root_node_id,  id_tracking[crawled_link])
            continue

        new_id = create_and_connect_graph(G, crawled_link, crawled_link, root_node_id)

        id_tracking[crawled_link] = new_id

    idx_node_now = 0
    while True:
        print(idx_node_now)
        try:
            curr_node = G.nodes[idx_node_now]
        except IndexError:
            break


        curr_node_id = curr_node["id"]
        curr_node_url = curr_node['url']

        link_list = get_all_links(url_extraction_count, req_get(curr_node_url), curr_node_url)
        for crawled_link in link_list:
            crawled_link = crawled_link.rstrip('/')

            # existing_id = id_tracking.get(crawled_link, None)
            if crawled_link in id_tracking:
                G.add_edge(curr_node_id,  id_tracking[crawled_link])
                continue

            new_id = create_and_connect_graph(G, crawled_link, crawled_link, curr_node_id)

            id_tracking[crawled_link] = new_id

        # for crawled_link in link_list:
        #     n_root_link_list = get_all_links(3, req_get(root_url), root_url)
        #     for i in n_root_link_list:
        #         create_and_connect_graph(G, i, i, curr_node_id)

        idx_node_now += 1

        if idx_node_now == max_depth:
            break


    # G.set_edge_smooth('continuous')
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
    # G.toggle_smoothing(False)

    if do_export_graph:
        export_graph(id_tracking, G.edges, G.nodes, 'exported_graph.pkl')


    print(id_tracking)
    G.show('nx.html',notebook=False)


        




        
    # G.show('nx.html',notebook=False)
