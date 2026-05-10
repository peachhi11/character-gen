from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import os
import yaml
from .exceptions import InvalidConfigError, ConfigError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "data" / "config" / "config.yaml"
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_env_file(env_path: Path = DEFAULT_ENV_PATH) -> Dict[str, str]:
    """Load simple KEY=VALUE pairs from .env without overriding real env vars."""
    loaded: Dict[str, str] = {}
    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue

        value = _strip_optional_quotes(value.strip())
        loaded[key] = value
        os.environ.setdefault(key, value)

    return loaded


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _is_openrouter_url(url: str) -> bool:
    return "openrouter.ai" in url.lower()


def resolve_api_url(file_value: Optional[str]) -> str:
    load_env_file()
    return _first_non_empty(
        os.getenv("CHARACTERGEN_API_URL"),
        file_value,
    ) or ""


def resolve_api_model(file_value: Optional[str]) -> Optional[str]:
    load_env_file()
    return _first_non_empty(
        os.getenv("CHARACTERGEN_API_MODEL"),
        os.getenv("OPENROUTER_MODEL"),
        file_value,
    )


def resolve_api_key(file_value: Optional[str] = None) -> Optional[str]:
    load_env_file()
    return _first_non_empty(
        os.getenv("CHARACTERGEN_API_KEY"),
        os.getenv("OPENROUTER_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        file_value,
    )

@dataclass
class ApiConfig:
    """API-related configuration"""
    url: str
    key: Optional[str] = None
    model: Optional[str] = None
    timeout: int = 420
    max_retries: int = 3
    retry_delay: int = 1

@dataclass
class GenerationConfig:
    """Generation-related settings"""
    max_tokens: int = 2048

@dataclass
class PathConfig:
    """File path configuration"""
    base_dir: Path = field(default_factory=lambda: PROJECT_ROOT)
    
    def __post_init__(self):
        self.data_dir = self.base_dir / "data"
        self.characters_dir = self.data_dir / "characters"
        self.base_prompts_dir = self.data_dir / "base_prompts"
        self.config_dir = self.data_dir / "config"
        self.logs_dir = self.data_dir / "logs"
        
        # Create directories if they don't exist
        for directory in [
            self.data_dir,
            self.characters_dir, 
            self.base_prompts_dir,
            self.config_dir,
            self.logs_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)

@dataclass
class AppConfig:
    """Main application configuration"""
    api: ApiConfig
    generation: GenerationConfig
    paths: PathConfig
    templates: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise InvalidConfigError("Config file must parse to a mapping")
            
            # Parse API configuration
            api_config = ApiConfig(
                url=resolve_api_url(data.get('API_URL')),
                key=resolve_api_key(data.get('API_KEY')),
                model=resolve_api_model(data.get('API_MODEL')),
            )
            
            # Parse generation settings
            gen_data = data.get('generation', {})
            gen_config = GenerationConfig(
                max_tokens=gen_data.get('max_tokens', 2048),
            )
            
            # Set up paths
            base_dir_value = data.get('base_dir')
            base_dir = (
                Path(base_dir_value).expanduser()
                if base_dir_value
                else PROJECT_ROOT
            )
            path_config = PathConfig(base_dir=base_dir)
            
            # Load templates
            template_path = path_config.config_dir / "template.json"
            templates = {}
            if template_path.exists():
                with open(template_path, 'r') as f:
                    import json
                    templates = json.load(f)
            
            config = cls(
                api=api_config,
                generation=gen_config,
                paths=path_config,
                templates=templates
            )
            config.validate()
            return config
            
        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Error parsing config file: {str(e)}")
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Error loading configuration: {str(e)}")
    
    def save(self, config_path: Path) -> None:
        """Save current configuration to YAML file"""
        try:
            config_data = {
                'API_URL': self.api.url,
                'API_MODEL': self.api.model or "",
                'generation': {
                    'max_tokens': self.generation.max_tokens,
                },
                'base_dir': str(self.paths.base_dir)
            }
            
            with open(config_path, 'w') as f:
                yaml.safe_dump(config_data, f, default_flow_style=False)
                
        except Exception as e:
            raise ConfigError(f"Error saving configuration: {str(e)}")
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.api.url:
            raise InvalidConfigError("API URL is required")
        
        if not self.paths.base_dir.exists():
            raise InvalidConfigError(f"Base directory does not exist: {self.paths.base_dir}")
        
        if self.generation.max_tokens <= 0:
            raise InvalidConfigError("generation.max_tokens must be greater than 0")

        if _is_openrouter_url(self.api.url):
            if not self.api.model or self.api.model == "replace-me":
                raise InvalidConfigError(
                    "OpenRouter requires API_MODEL in data/config/config.yaml "
                    "or CHARACTERGEN_API_MODEL in the environment"
                )
            if not self.api.key or self.api.key == "replace-me":
                raise InvalidConfigError(
                    "OpenRouter requires an API key in .env "
                    "(OPENROUTER_API_KEY or CHARACTERGEN_API_KEY)"
                )
        
        return True

# Global configuration instance
_config: Optional[AppConfig] = None

def get_config() -> AppConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        if not DEFAULT_CONFIG_PATH.exists():
            raise ConfigError("Configuration file not found")
        _config = AppConfig.load(DEFAULT_CONFIG_PATH)
    return _config

def set_config(config: AppConfig) -> None:
    """Set the global configuration instance"""
    global _config
    _config = config
