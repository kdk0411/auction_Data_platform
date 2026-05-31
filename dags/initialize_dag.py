import os
from datetime import datetime

from airflow import DAG
from operators.initialize_operators import (
    ExtractItemListOperator,
    TransformItemsOperator,
    LoadToMinIOOperator,
)

with DAG(
    dag_id="initialize_item_db",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["initialize", "info"],
) as dag:

    extract = ExtractItemListOperator(
        task_id="extract",
        js_path="/opt/airflow/include/search_lists.js",
        queue="info",
    )

    transform = TransformItemsOperator(
        task_id="transform",
        extract_task_id="extract",
        base_url="https://xn--o80b01o9mlw3kdzc.com/item_detail/",
        queue="info",
    )

    load = LoadToMinIOOperator(
        task_id="load",
        transform_task_id="transform",
        bucket="auction",
        object_key="initialize/parsed_items.json",
        endpoint_url=os.environ.get("MINIO_ENDPOINT_URL", "http://test-minio:9000"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "auction_admin"),
        secret_key=os.environ.get("MINIO_SECRET_KEY", "test1234!"),
        queue="info",
    )

    extract >> transform >> load
