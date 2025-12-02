import requests
from typing import Any, Dict
from .config import AuroraEnvConfig

class AuroraAgentClient:
    """
    Client to interact with the Agent within the Aurora Environment.
    """
    def __init__(self, config: AuroraEnvConfig):
        self.config = config
        self.endpoint = config.get_endpoint_url()

    def invoke_agent(self, input_data: Any) -> Any:
        """
        Sends input to the agent and retrieves the output.
        In a real implementation, this would make an HTTP request to the Aurora Env.
        """
        print(f"Connecting to Aurora Env: {self.config.env_id} (v{self.config.env_version})")
        print(f"Invoking Agent: {self.config.agent_name} at {self.endpoint}")
        
        # TODO: Replace with actual HTTP call
        # response = requests.post(self.endpoint, json={"input": input_data})
        # return response.json()

        # Mock response for POC purposes
        return self._mock_response(input_data)

    def _mock_response(self, input_data: Any) -> str:
        # Simple mock logic to simulate an agent response
        if isinstance(input_data, dict) and "question" in input_data:
            return f"Mock Answer from {self.config.agent_name} for: {input_data['question']}"
        return f"Processed: {str(input_data)}"
