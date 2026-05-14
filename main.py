import requests
from pyvis.network import Network
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urlparse
from collections import deque
import pickle
import time


# ─── helpers ──────────────────────────────────────────────────────────────────

def check_url_type(url):
    parsed = urlparse(url)
    if parsed.scheme in ['http', 'https']:
        return "full"
    if parsed.netloc != "" or url.startswith("//"):
        return "hostname"
    if url.startswith('/'):
        return "path"
    return "unknown"


def req_get(url, retries=2):
    ua = UserAgent()
    headers = {'User-Agent': ua.chrome}
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            return response.text
        except Exception as e:
            if attempt == retries:
                print(f"  [WARN] Failed to fetch {url}: {e}")
                return ""
            time.sleep(1)


def get_all_links(n, html, url):
    """Extract up to n Wikipedia article links from html."""
    if not html:
        return []
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    soup = BeautifulSoup(html, 'html.parser')
    content = soup.find("div", id="mw-content-text")
    if not content:
        return []

    internal_namespaces = (
        'File:', 'Category:', 'Help:', 'Special:',
        'Template:', 'Talk:', 'Portal:', 'Wikipedia:'
    )

    all_links = []
    count = 0
    for a_tag in content.find_all("a"):
        if isinstance(n, int) and count >= n:
            break

        href = a_tag.get('href')
        if not href or not isinstance(href, str) or len(href) == 0:
            continue
        if href[0] == '#':
            continue
        if "/wiki/" not in href:
            continue
        if any(ns in href for ns in internal_namespaces):
            continue

        url_type = check_url_type(href)
        if url_type == "full":
            link = href.split("?")[0]
        elif url_type == "hostname":
            link = f"{parsed.scheme}:{href}"
        else:
            link = f"{base_url}{href.split('?')[0]}"

        all_links.append(link.rstrip('/'))
        count += 1

    return all_links


# ─── BFS shortest-path search ─────────────────────────────────────────────────

def bfs_find_target(
    root_url: str,
    target_key: str,
    links_per_page: int = 10,
    max_pages: int = 500,
    verbose: bool = True,
) -> dict:
    """
    BFS from root_url until a URL containing target_key is found.

    Returns a dict:
        {
            "found"       : bool,
            "target_url"  : str | None,
            "path"        : list[str],   # root → target
            "depth"       : int,
            "pages_visited": int,
            "graph_nodes" : dict[url -> id],
            "graph_edges" : list[(from_id, to_id)],
        }
    """
    target_key_lower = target_key.lower()
    root_url = root_url.rstrip('/')

    # BFS state
    visited   = {root_url}
    parent    = {root_url: None}   # url -> parent url (for path reconstruction)
    queue     = deque([root_url])

    # Graph tracking (for visualisation)
    node_id   = {root_url: 1}
    edges     = []                  # list of (from_id, to_id)
    pages_visited = 0

    if verbose:
        print(f"[BFS] Starting from: {root_url}")
        print(f"[BFS] Searching for key: '{target_key}'\n")

    while queue:
        current_url = queue.popleft()
        curr_id     = node_id[current_url]
        pages_visited += 1

        depth = 0
        tmp = current_url
        while parent[tmp] is not None:
            depth += 1
            tmp = parent[tmp]

        if verbose:
            print(f"  [{pages_visited}/{max_pages}] depth={depth}  {current_url}")

        # ── fetch & extract links ──────────────────────────────────────────
        html  = req_get(current_url)
        links = get_all_links(links_per_page, html, current_url)

        for link in links:
            link = link.rstrip('/')

            # assign graph id
            if link not in node_id:
                node_id[link] = len(node_id) + 1

            edges.append((curr_id, node_id[link]))

            # ── TARGET FOUND? ──────────────────────────────────────────────
            if target_key_lower in link.lower():
                parent[link] = current_url  # record final edge

                # reconstruct path
                path = []
                step = link
                while step is not None:
                    path.append(step)
                    step = parent[step]
                path.reverse()

                if verbose:
                    print(f"\n✅  TARGET FOUND: {link}")
                    print(f"    Depth        : {len(path) - 1}")
                    print(f"    Pages visited: {pages_visited}")
                    print(f"\n    Path:")
                    for i, p in enumerate(path):
                        prefix = "  ROOT →" if i == 0 else (f"  {'→':>5}" if i < len(path)-1 else "  TARGET→")
                        print(f"    {i:>2}. {p}")

                return {
                    "found"        : True,
                    "target_url"   : link,
                    "path"         : path,
                    "depth"        : len(path) - 1,
                    "pages_visited": pages_visited,
                    "graph_nodes"  : node_id,
                    "graph_edges"  : edges,
                }

            # ── enqueue unseen ─────────────────────────────────────────────
            if link not in visited:
                visited.add(link)
                parent[link] = current_url
                queue.append(link)

        if pages_visited >= max_pages:
            if verbose:
                print(f"\n⛔  Reached max_pages limit ({max_pages}) without finding target.")
            break

    return {
        "found"        : False,
        "target_url"   : None,
        "path"         : [],
        "depth"        : -1,
        "pages_visited": pages_visited,
        "graph_nodes"  : node_id,
        "graph_edges"  : edges,
    }


# ─── visualisation ────────────────────────────────────────────────────────────

def build_graph(result: dict, show_full_graph: bool = True) -> Network:
    G = Network('85vh', '100%')

    node_id   = result["graph_nodes"]
    id_to_url = {v: k for k, v in node_id.items()}
    path_set  = set(result["path"])
    path_edges = set()

    if result["found"]:
        path_list = result["path"]
        for i in range(len(path_list) - 1):
            a = node_id[path_list[i]]
            b = node_id[path_list[i + 1]]
            path_edges.add((a, b))

    # nodes
    for url, nid in node_id.items():
        if not show_full_graph and url not in path_set:
            continue
        label = url.split("/wiki/")[-1] if "/wiki/" in url else url
        color = "#ff6b6b" if url == result.get("target_url") else \
                "#ffd93d" if url in path_set else \
                "#82b1ff"
        border = "#c0392b" if url == result.get("target_url") else \
                 "#f39c12" if url in path_set else \
                 "#4e83d1"
        size   = 12 if url in path_set else 4
        G.add_node(nid, label=label, title=url, color={"background": color, "border": border}, size=size)

    # edges
    added_edges = set()
    for (a, b) in result["graph_edges"]:
        if not show_full_graph and (id_to_url.get(a) not in path_set or id_to_url.get(b) not in path_set):
            continue
        key = (min(a,b), max(a,b))
        if key in added_edges:
            continue
        added_edges.add(key)
        is_path_edge = (a, b) in path_edges or (b, a) in path_edges
        G.add_edge(a, b,
                   color={"color": "#ff6b6b" if is_path_edge else "#4e83d1",
                          "opacity": 1.0 if is_path_edge else 0.25},
                   width=3 if is_path_edge else 1)

    G.barnes_hut(gravity=-12000, central_gravity=0.1,
                 spring_length=300, spring_strength=0.005, damping=0.9)
    G.set_options("""
    {
        "nodes": {
            "font": { "face": "arial", "size": 7 },
            "borderWidth": 1
        },
        "edges": { "smooth": false }
    }
    """)
    return G


def export_result(result: dict, filename: str = "bfs_result.pkl"):
    with open(filename, 'wb') as f:
        pickle.dump(result, f)
    print(f"[export] Saved to {filename}")


# ─── loader ───────────────────────────────────────────────────────────────────

def load_and_show(
    filename: str = "bfs_result.pkl",
    show_full_graph: bool = True,
    output_html: str = "loaded_graph.html",
) -> dict:
    """
    Load a bfs_result.pkl and:
      - Print the shortest path to console (if found)
      - Render graph HTML with the path highlighted

    Returns the raw result dict.
    """
    with open(filename, 'rb') as f:
        result = pickle.load(f)

    # ── print route ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  File          : {filename}")
    print(f"  Target key    : searched in URLs")
    print(f"  Target found  : {result['found']}")
    print(f"  Pages crawled : {result['pages_visited']}")

    if result['found']:
        print(f"  Target URL    : {result['target_url']}")
        print(f"  Shortest depth: {result['depth']}")
        print(f"\n  Shortest path ({result['depth']} hop(s)):")
        for i, url in enumerate(result['path']):
            marker = " [ROOT]  " if i == 0 else \
                     " [TARGET]" if i == len(result['path']) - 1 else \
                     f"   [{i}]   "
            print(f"    {marker} {url}")
    else:
        print("  Target not found within crawl budget.")

    print(f"{'='*60}\n")

    # ── build & save graph ────────────────────────────────────────────────────
    G = build_graph(result, show_full_graph=show_full_graph)
    G.show(output_html, notebook=False)
    print(f"[load_and_show] Graph saved → {output_html}")

    return result


# ─── main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    ROOT_URL          = 'https://id.wikipedia.org/wiki/Indonesia'
    TARGET_KEY        = 'soekarno'
    LINKS_PER_PAGE    = 10      # how many links to follow per page
    MAX_PAGES         = 300     # BFS budget
    SHOW_FULL_GRAPH   = True    # False = only draw the shortest path
    DO_EXPORT         = True

    result = bfs_find_target(
        root_url       = ROOT_URL,
        target_key     = TARGET_KEY,
        links_per_page = LINKS_PER_PAGE,
        max_pages      = MAX_PAGES,
        verbose        = True,
    )

    if DO_EXPORT:
        export_result(result, "bfs_result.pkl")

    # tampilkan route + graph sekaligus
    load_and_show(
        filename        = "bfs_result.pkl",
        show_full_graph = SHOW_FULL_GRAPH,
        output_html     = "bfs_graph.html",
    )
    print("[done]")