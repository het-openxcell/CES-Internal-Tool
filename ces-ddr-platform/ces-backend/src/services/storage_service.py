from src.config.manager import settings
from src.external.s3_client import S3Client


class StorageService:
    def __init__(self, s3_client: S3Client | None = None) -> None:
        self.s3 = s3_client or S3Client()
        self.key_prefix = settings.S3_KEY_PREFIX

    def build_original_key(self, ddr_id: str) -> str:
        return f"{self.key_prefix}ddrs/{ddr_id}/original.pdf"

    def build_chunk_key(self, ddr_id: str, date: str) -> str:
        return f"{self.key_prefix}ddrs/{ddr_id}/chunks/{date}.pdf"

    async def upload_pdf(self, ddr_id: str, data: bytes) -> str:
        key = self.build_original_key(ddr_id)
        await self.s3.put_object(key, data)
        return key

    async def upload_chunk(self, ddr_id: str, date: str, data: bytes) -> str:
        key = self.build_chunk_key(ddr_id, date)
        await self.s3.put_object(key, data)
        return key

    async def download(self, key: str) -> bytes:
        return await self.s3.get_object(key)

    async def download_original(self, ddr_id: str) -> bytes:
        key = self.build_original_key(ddr_id)
        return await self.s3.get_object(key)

    async def download_chunk(self, ddr_id: str, date: str) -> bytes:
        key = self.build_chunk_key(ddr_id, date)
        return await self.download(key)

    async def delete_ddr(self, ddr_id: str) -> None:
        prefix = f"{self.key_prefix}ddrs/{ddr_id}/"
        keys = await self.s3.list_keys(prefix)
        if keys:
            await self.s3.delete_objects(keys)
