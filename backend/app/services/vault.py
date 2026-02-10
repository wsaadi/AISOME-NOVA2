import hvac
from typing import Optional
from app.config import get_settings

settings = get_settings()


class VaultService:
    def __init__(self):
        self.client = hvac.Client(url=settings.VAULT_ADDR, token=settings.VAULT_TOKEN)
        self._ensure_secrets_engine()

    def _ensure_secrets_engine(self):
        try:
            engines = self.client.sys.list_mounted_secrets_engines()
            mount = f"{settings.VAULT_MOUNT_POINT}/"
            if mount not in engines.get("data", engines):
                self.client.sys.enable_secrets_engine(
                    backend_type="kv",
                    path=settings.VAULT_MOUNT_POINT,
                    options={"version": "2"},
                )
        except Exception:
            pass

    def store_api_key(self, provider_slug: str, api_key: str) -> bool:
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=f"llm-providers/{provider_slug}",
                secret={"api_key": api_key},
                mount_point=settings.VAULT_MOUNT_POINT,
            )
            return True
        except Exception:
            return False

    def get_api_key(self, provider_slug: str) -> Optional[str]:
        try:
            secret = self.client.secrets.kv.v2.read_secret_version(
                path=f"llm-providers/{provider_slug}",
                mount_point=settings.VAULT_MOUNT_POINT,
            )
            return secret["data"]["data"].get("api_key")
        except Exception:
            return None

    def delete_api_key(self, provider_slug: str) -> bool:
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=f"llm-providers/{provider_slug}",
                mount_point=settings.VAULT_MOUNT_POINT,
            )
            return True
        except Exception:
            return False

    def has_api_key(self, provider_slug: str) -> bool:
        return self.get_api_key(provider_slug) is not None


def get_vault_service() -> VaultService:
    return VaultService()
