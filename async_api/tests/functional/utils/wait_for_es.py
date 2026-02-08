import time

from elasticsearch import Elasticsearch
from tests.functional.settings import test_settings


if __name__ == "__main__":
    es_client = Elasticsearch(hosts=test_settings.es_url)
    while True:
        if es_client.ping():
            break
        print("Waiting for Elasticsearch to be available...")
        time.sleep(1)
