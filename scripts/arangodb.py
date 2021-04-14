from arango import ArangoClient, DocumentInsertError

import singleton as singleton


class ArangoDB(metaclass=singleton.Singleton):

    def __init__(self):
        client = ArangoClient(hosts='http://10.4.8.146:8529')
        sys_db = client.db('_system', username='root', password='')

        if not sys_db.has_database('tor'):
            sys_db.create_database('tor')

        self.db = client.db('tor', username='root', password='')

        if self.db.has_graph('darkweb'):
            self.graph = self.db.graph('darkweb')
        else:
            self.graph = self.db.create_graph('darkweb')

        if not self.graph.has_vertex_collection("domains"):
            self.domains = self.graph.create_vertex_collection("domains")
        else:
            self.domains = self.graph.vertex_collection("domains")

        if not self.graph.has_edge_definition("edges"):
            self.edges = self.graph.create_edge_definition(
                edge_collection="edges",
                from_vertex_collections=["domains"],
                to_vertex_collections=["domains"])
        else:
            self.edges = self.graph.edge_collection("edges")

    def insert_domain(self, domain):
        try:
            self.domains.insert({'_key': domain})
        except DocumentInsertError:
            pass

    def insert_edge(self, from_vtx, to_vtx, weight):
        edge = self.create_edge(from_vtx, to_vtx, weight)
        try:
            self.edges.insert(edge)
        except DocumentInsertError:
            pass

    def batch_insert(self, domains, edges):
        batch_db = self.db.begin_batch_execution(return_result=False)
        batch_domains = batch_db.collection('domains')
        batch_edges = batch_db.collection('edges')
        for domain in domains:
            batch_domains.insert({'_key': domain})
        for from_vtx, to_vtx, weight in edges:
            batch_edges.insert(self.create_edge(from_vtx, to_vtx, weight))

        batch_db.commit()

    @staticmethod
    def create_edge(from_vtx, to_vtx, weight):
        edge = dict()
        edge['_from'] = 'domains/{0}'.format(from_vtx)
        edge['_to'] = 'domains/{0}'.format(to_vtx)
        edge['weight'] = weight

        return edge
