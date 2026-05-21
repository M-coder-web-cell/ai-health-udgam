import os
import json
import networkx as nx
from networkx.readwrite import json_graph

class HealthGraphManager:
    def __init__(self, file_path="server_storage/health_graph.json"):
        self.file_path = file_path
        self.graph = nx.DiGraph()
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.graph = json_graph.node_link_graph(json.load(f))
            except Exception as e:
                self.graph = nx.DiGraph()

    def _save(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(json_graph.node_link_data(self.graph), f, indent=2)

    def add_relationship(self, source, source_type, target, target_type, rel_type):
        source, target = source.lower().strip(), target.lower().strip()
        
        for node, n_type in [(source, source_type), (target, target_type)]:
            if not self.graph.has_node(node):
                self.graph.add_node(node, type=n_type, label=node)
                
        self.graph.add_edge(source, target, type=rel_type)
        self._save()

    def get_user_subgraph(self, user_node="user"):
        if not self.graph.has_node(user_node):
            return {"nodes": [], "edges": []}
        
        try:
            reachable = nx.single_source_shortest_path_length(self.graph.to_undirected(), user_node, cutoff=2)
            sub_g = self.graph.subgraph(reachable.keys())
            return {
                "nodes": [{"id": n, "label": attrs.get("label", n), "type": attrs.get("type")} for n, attrs in sub_g.nodes(data=True)],
                "edges": [{"source": u, "target": v, "type": attrs.get("type")} for u, v, attrs in sub_g.edges(data=True)]
            }
        except:
            return {"nodes": [], "edges": []}

    def find_clinical_paths(self, user_node, ingredients):
        paths = []
        if not self.graph.has_node(user_node):
            return []
            
        user_health_nodes = [t for _, t, d in self.graph.edges(user_node, data=True) if d.get("type") in ["HAS_CONDITION", "HAS_ALLERGY", "HAS_GOAL"]]
        
        for entity in user_health_nodes:
            for ing in ingredients:
                ing_key = ing.lower().strip()
                if self.graph.has_node(ing_key) and nx.has_path(self.graph, entity, ing_key):
                    path = nx.shortest_path(self.graph, entity, ing_key)
                    steps = []
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        steps.append(f"({u}) -[{self.graph.edges[u,v].get('type')}]->")
                    steps.append(f"({path[-1]})")
                    paths.append(" ".join(steps))
        return paths

    def get_node_neighbors(self, node_id):
        node_key = node_id.lower().strip()
        if not self.graph.has_node(node_key):
            return {"exists": False}
        return {
            "exists": True,
            "incoming": [{"source": u, "type": d.get("type")} for u, v, d in self.graph.in_edges(node_key, data=True)],
            "outgoing": [{"target": v, "type": d.get("type")} for u, v, d in self.graph.out_edges(node_key, data=True)]
        }
