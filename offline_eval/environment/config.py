from dataclasses import dataclass, asdict
from typing import Optional
import json

@dataclass
class AuroraEnvConfig:
    """
    Configuration for the AI Application Environment (Aurora Env).
    This represents the data that would be stored/configured via UI.
    """
    env_id: str
    env_version: str
    agent_name: str
    description: Optional[str] = None
    
    # In a real scenario, the endpoint URL might be dynamically resolved 
    # based on env_id/version, or stored explicitly.
    # For this POC, we'll allow it to be explicit or derived.
    api_endpoint: Optional[str] = None

    def get_endpoint_url(self) -> str:
        if self.api_endpoint:
            return self.api_endpoint
        # Mock resolution logic based on Aurora Env conventions
        return f"https://aurora-gateway.microsoft.com/envs/{self.env_id}/v{self.env_version}/agents/{self.agent_name}"

    @classmethod
    def from_json(cls, json_str: str) -> 'AuroraEnvConfig':
        data = json.loads(json_str)
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)
