from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json

@dataclass
class EvaluatorConfig:
    """
    Configuration for a single evaluator.
    """
    name: str  # e.g., "Groundedness", "Exact Match"
    category: str # "Automated - Statistical", "Automated - Semantic", "Automated - Rule-based", "LLM-as-a-judge", "Human"
    type: str  # "azure-builtin", "custom-service", "local-function"
    
    # For built-in: The specific metric name in Azure AI SDK (e.g., "Groundedness")
    # For custom: The service endpoint URL
    # For local: The function name or identifier
    target: str 
    
    # Threshold for pass/fail (0.0 to 1.0 or 1 to 5 depending on metric)
    pass_threshold: Optional[float] = None
    
    # Additional parameters for the evaluator (e.g., model deployment name for AI-assisted evals)
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EvaluationSuiteConfig:
    """
    Configuration for the entire evaluation suite to be run.
    """
    suite_name: str
    evaluators: List[EvaluatorConfig]

    @classmethod
    def from_json(cls, json_str: str) -> 'EvaluationSuiteConfig':
        data = json.loads(json_str)
        evaluators = [EvaluatorConfig(**e) for e in data.get("evaluators", [])]
        return cls(suite_name=data.get("suite_name"), evaluators=evaluators)
