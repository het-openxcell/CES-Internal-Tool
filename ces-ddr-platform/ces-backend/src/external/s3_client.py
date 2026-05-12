import asyncio
from typing import Any

import boto3

from src.config.manager import settings
from src.utilities.logging.logger import logger


class S3Client:
    def __init__(
        self,
        bucket: str | None = None,
        region: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket or settings.S3_BUCKET_NAME
        self._region = region or settings.S3_REGION
        self._access_key_id = access_key_id or settings.S3_ACCESS_KEY_ID
        self._secret_access_key = secret_access_key or settings.S3_SECRET_ACCESS_KEY
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=self._region,
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._secret_access_key,
            )
        return self._client

    async def put_object(self, key: str, body: bytes) -> None:
        client = self._get_client()
        await asyncio.to_thread(
            client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=body,
        )
        logger.info(f"S3 put_object: {key}")

    async def get_object(self, key: str) -> bytes:
        client = self._get_client()
        response = await asyncio.to_thread(
            client.get_object,
            Bucket=self._bucket,
            Key=key,
        )
        return await asyncio.to_thread(response["Body"].read)

    async def delete_object(self, key: str) -> None:
        client = self._get_client()
        await asyncio.to_thread(
            client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )
        logger.info(f"S3 delete_object: {key}")

    async def list_keys(self, prefix: str) -> list[str]:
        client = self._get_client()
        keys: list[str] = []
        paginator = client.get_paginator("list_objects_v2")

        def _page():
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])

        await asyncio.to_thread(_page)
        return keys

    async def delete_objects(self, keys: list[str]) -> None:
        if not keys:
            return
        client = self._get_client()
        batch_size = 1000
        for i in range(0, len(keys), batch_size):
            batch = [{"Key": k} for k in keys[i : i + batch_size]]
            await asyncio.to_thread(
                client.delete_objects,
                Bucket=self._bucket,
                Delete={"Objects": batch, "Quiet": True},
            )
        logger.info(f"S3 delete_objects: {len(keys)} keys")
