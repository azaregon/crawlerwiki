from main import load_and_show

result = load_and_show(
    filename        = "bfs_result.pkl",
    show_full_graph = True,       # False = only show shortest path
    output_html     = "my_graph.html",
)