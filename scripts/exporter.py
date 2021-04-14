import logging
import re
from collections import Counter
from urllib.parse import urlparse

from elasticsearch import Elasticsearch
from tqdm import tqdm

from arangodb import ArangoDB

GET_DOMAINS_QUERY = {
    "bool": {
        "must": {
            "multi_match": {
                "query": "tor",
                "fields": ["source"]
            }
        },
        "filter": {
            "exists": {
                "field": "info.external_urls.href_urls.tor"
            }
        }
    }
}


def build_domain_list(record):
    return [
        {
            'domain': i["_source"]['info']['domain'],
            'tor': i["_source"]['info']['external_urls']['href_urls']['tor']
        } for i in record
    ]


def get_domain(url):
    net_loc = urlparse(url).netloc
    domain_levels = re.split("[.:]", net_loc)
    for idx, oni in enumerate(domain_levels):
        if idx == 0:
            continue
        if oni == "onion" and len(domain_levels[idx - 1]) in (16, 56):
            return domain_levels[idx - 1] + "." + oni


def add_to_set(st, item):
    if item in st:
        st.add(item)


def export_to_arango(domains):
    db = ArangoDB()
    for domain, urls in tqdm(domains.items()):
        domain_nodes = set()
        edges = list()
        domain_nodes.add(domain)
        for url, count in urls.items():
            domain_nodes.add(url)
            edges.append((domain, url, count))
        db.batch_insert(domain_nodes, edges)


def get_es_records():
    es = Elasticsearch(['http://10.4.8.146:9200'], retry_on_timeout=True)
    step_size = 1000
    scroll_timeout = '60m'

    res = es.search(index="crawlers_v2", body={
        "size": step_size,
        "track_total_hits": "true",
        "_source": {
            "includes": ["info.domain", "info.external_urls.href_urls.tor"]
        },
        "query": GET_DOMAINS_QUERY,
    }, scroll=scroll_timeout)

    results = [i["_source"] for i in res["hits"]["hits"]]
    total = res['hits']['total']['value']
    scroll_id = res['_scroll_id']

    logging.info("No. of total hits: ", total)
    step_range = range(step_size, total, step_size)
    logging.info("No. of steps to get all the documents:", len(step_range))

    for step in tqdm(step_range):
        res = es.scroll(scroll_id=scroll_id, scroll=scroll_timeout)
        scroll_id = res['_scroll_id']
        results.extend([i["_source"] for i in res["hits"]["hits"]])

    return results


def main():
    records = get_es_records()
    domains = dict()
    for record in records:
        domain = record['info']['domain']
        tor_urls = [get_domain(url) for url in record['info']['external_urls']['href_urls']['tor']]
        if domain in domains:
            domains[domain].extend(tor_urls)
        else:
            domains[domain] = tor_urls
    for from_domain, to_domains in domains.items():
        domains[from_domain] = Counter(to_domains)
    records.clear()
    export_to_arango(domains)


if __name__ == "__main__":
    main()
