from arango import ArangoClient, DocumentInsertError

import singleton as singleton


class ArangoDB(metaclass=singleton.Singleton):

    def __init__(self):
        client = ArangoClient(hosts='http://10.4.8.146:8529')
        sys_db = client.db('_system', username='root', password='')

        if not sys_db.has_database('tor'):
            sys_db.create_database('tor')

        self.db = client.db('tor', username='root', password='')

        if not self.db.has_graph('darkweb'):
            self.db.create_collection(name='domains', shard_fields=['_key'], shard_count=8)
            self.db.create_collection(name='edges', edge=True, shard_fields=['vertex'],
                                      shard_count=8, shard_like='domains')
            self.db.create_graph(name='darkweb', edge_definitions=[{
                'edge_collection': 'edges',
                'from_vertex_collections': ['domains'],
                'to_vertex_collections': ['domains']
            }], shard_count=8)
        self.graph = self.db.graph('darkweb')
        self.domains = self.graph.vertex_collection("domains")
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
        edge['vertex'] = from_vtx
        edge['weight'] = weight

        return edge
