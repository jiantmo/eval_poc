from typing import List, Dict, Any
from dataclasses import dataclass
from dataset.model import EvalRecord
from environment.config import AuroraEnvConfig
from environment.client import AuroraAgentClient

@dataclass
class ExecutionResult:
    record: EvalRecord
    actual_output: Any
    error: str = None

class EvalRunner:
    """
    Orchestrates the evaluation process:
    1. Reads the dataset
    2. Configures the environment
    3. Runs inputs through the agent
    4. Collects outputs
    """
    def __init__(self, env_config: AuroraEnvConfig):
        self.env_client = AuroraAgentClient(env_config)

    def run_dataset(self, dataset: List[EvalRecord]) -> List[ExecutionResult]:
        results = []
        print(f"Starting evaluation run on {len(dataset)} records...")
        
        for i, record in enumerate(dataset):
            print(f"Processing record {i+1}/{len(dataset)}")
            try:
                # Extract input from the record
                # Assuming the agent expects the whole 'input' object or specific fields
                # Adjust based on actual API contract
                agent_input = record.input
                
                # Invoke Agent
                actual_output = self.env_client.invoke_agent(agent_input)
                
                results.append(ExecutionResult(
                    record=record,
                    actual_output=actual_output
                ))
            except Exception as e:
                print(f"Error processing record {i}: {e}")
                results.append(ExecutionResult(
                    record=record,
                    actual_output=None,
                    error=str(e)
                ))
                
        return results
