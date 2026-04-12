import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from dotenv import load_dotenv

CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"


class Config:
    _instance: Optional["Config"] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        load_dotenv()
        
        if not CONFIG_FILE.exists():
            raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")
        
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)
        
        self._resolve_env_vars()

    def _resolve_env_vars(self):
        def resolve_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.getenv(env_var, "")
            return value

        def resolve_dict(d):
            result = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    result[k] = resolve_dict(v)
                else:
                    result[k] = resolve_value(v)
            return result

        self._config = resolve_dict(self._config)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def log_api_base_url(self) -> str:
        return self.get("log.api.base_url", "http://localhost:8080")

    @property
    def log_api_key(self) -> str:
        return self.get("log.api.api_key", "")

    @property
    def log_api_timeout(self) -> int:
        return self.get("log.api.timeout", 30)

    @property
    def llm_provider(self) -> str:
        return self.get("llm.provider", "deepseek")

    @property
    def llm_config(self) -> Dict[str, Any]:
        provider = self.llm_provider
        return self.get(f"llm.providers.{provider}", {})

    @property
    def project_root(self) -> str:
        return self.get("project.root_dir", "")

    @property
    def java_package_base(self) -> str:
        return self.get("project.java_package_base", "com.example")

    @property
    def server_host(self) -> str:
        return self.get("server.host", "127.0.0.1")

    @property
    def server_port(self) -> int:
        return self.get("server.port", 8765)


config = Config()
