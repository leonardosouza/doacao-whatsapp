"""Gera imagem PNG do grafo LangGraph do DoaZap."""

import os
import sys


def generate_img_graph(graph):
    current_file = os.path.basename(__import__('sys').argv[0]).split(".")[0]
    with open(f"{current_file}.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())
    print(f"Arquivo '{current_file}.png' gerado com sucesso.")


if __name__ == "__main__":
    from app.agent.graph import build_graph

    graph = build_graph(db=None, conversation=None)
    generate_img_graph(graph)
