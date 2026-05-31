from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from typing import Any

import boto3
import requests
from airflow.models import BaseOperator
from botocore.client import Config
from botocore.exceptions import ClientError

from parsers.maple_item_parser import parse_item

log = logging.getLogger(__name__)


class ExtractItemListOperator(BaseOperator):
    """search_lists.js 에서 아이템 목록을 추출해 XCom에 푸시한다."""

    def __init__(self, js_path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.js_path = js_path

    def execute(self, context: Any) -> list[dict]:
        text = Path(self.js_path).read_text(encoding="utf-8")
        m = re.search(r"var\s+ITEMS\s*=\s*(\[[\s\S]*?\]);", text)
        if not m:
            raise ValueError(f"var ITEMS not found in {self.js_path}")
        items = ast.literal_eval(m.group(1))
        log.info("Extracted %d items from %s", len(items), self.js_path)
        return items


class TransformItemsOperator(BaseOperator):
    """아이템 목록을 받아 메이플노트를 스크래핑하고 in-memory 파싱한다."""

    def __init__(
        self,
        extract_task_id: str,
        base_url: str,
        request_timeout: int = 15,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.extract_task_id = extract_task_id
        self.base_url = base_url
        self.request_timeout = request_timeout

    def execute(self, context: Any) -> list[dict]:
        items: list[dict] = context["ti"].xcom_pull(task_ids=self.extract_task_id)
        results = []
        skipped = 0

        for i, item in enumerate(items):
            item_id = item["code"]
            try:
                resp = requests.get(
                    self.base_url + str(item_id),
                    timeout=self.request_timeout,
                )
                if "home-wrap" in resp.text or "<main" not in resp.text:
                    skipped += 1
                    continue
                doc = parse_item(resp.text, item_id)
                if doc:
                    results.append(doc)
            except Exception as e:
                log.warning("Failed item_id=%s: %s", item_id, e)
                skipped += 1

            if (i + 1) % 100 == 0:
                log.info(
                    "Progress: %d/%d  parsed=%d  skipped=%d",
                    i + 1, len(items), len(results), skipped,
                )

        log.info("Done: parsed=%d  skipped=%d", len(results), skipped)
        return results


class LoadToMinIOOperator(BaseOperator):
    """파싱된 아이템 목록을 MinIO(S3 호환)에 JSON으로 적재한다."""

    def __init__(
        self,
        transform_task_id: str,
        bucket: str,
        object_key: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.transform_task_id = transform_task_id
        self.bucket = bucket
        self.object_key = object_key
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key

    def execute(self, context: Any) -> None:
        parsed_items: list[dict] = context["ti"].xcom_pull(task_ids=self.transform_task_id)

        s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

        try:
            s3.head_bucket(Bucket=self.bucket)
        except ClientError:
            s3.create_bucket(Bucket=self.bucket)
            log.info("Created bucket: %s", self.bucket)

        body = json.dumps(parsed_items, ensure_ascii=False, indent=2).encode("utf-8")
        s3.put_object(
            Bucket=self.bucket,
            Key=self.object_key,
            Body=body,
            ContentType="application/json",
        )
        log.info(
            "Uploaded %d items → s3://%s/%s",
            len(parsed_items), self.bucket, self.object_key,
        )
