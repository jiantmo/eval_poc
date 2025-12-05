from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import random

# In a real scenario, we would import from azure.ai.evaluation
# from azure.ai.evaluation import GroundednessEvaluator, RelevanceEvaluator, ...

class BaseEvaluator(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def evaluate(self, input_data: Any, actual_output: Any, expected_output: Any) -> Dict[str, Any]:
        """
        Returns a dictionary containing the score and any reasoning.
        e.g., {"score": 4.5, "reasoning": "..."}
        """
        pass

class AzureBuiltInEvaluator(BaseEvaluator):
    """
    Wrapper for Azure AI Foundry Evaluation SDK evaluators.
    Used for:
    - Automated - Semantic (Similarity)
    - LLM-as-a-judge (Groundedness, Relevance, Coherence, Fluency)
    """
    def evaluate(self, input_data: Any, actual_output: Any, expected_output: Any) -> Dict[str, Any]:
        metric_name = self.config.target
        print(f"  [AzureBuiltIn] Running {metric_name} evaluation...")
        
        # Mocking result for POC
        # For similarity, usually 0-1 or 1-5. For LLM judges usually 1-5.
        mock_score = round(random.uniform(2.5, 5.0), 1)
        return {
            "metric": metric_name,
            "score": mock_score,
            "passed": mock_score >= (self.config.pass_threshold or 0),
            "reasoning": f"Mock Azure AI reasoning for {metric_name}."
        }

class LocalFunctionEvaluator(BaseEvaluator):
    """
    Runs local python functions for statistical or rule-based checks.
    Used for:
    - Automated - Statistical (Exact Match, F1)
    - Automated - Rule-based (Keyword presence, JSON schema)
    """
    def evaluate(self, input_data: Any, actual_output: Any, expected_output: Any) -> Dict[str, Any]:
        func_name = self.config.target
        print(f"  [LocalFunction] Running {func_name}...")
        
        score = 0.0
        reasoning = ""
        passed = False

        # Mock implementation of various local functions
        if func_name == "exact_match":
            # Simple string equality
            is_match = str(actual_output).strip() == str(expected_output.get("answer", "")).strip() if isinstance(expected_output, dict) else str(actual_output) == str(expected_output)
            score = 1.0 if is_match else 0.0
            reasoning = "Strings match exactly." if is_match else "Strings do not match."
        
        elif func_name == "f1_score":
            # Mock F1 score
            score = round(random.uniform(0.5, 1.0), 2)
            reasoning = "Calculated token overlap."

        elif func_name == "keyword_check":
            keywords = self.config.parameters.get("keywords", [])
            found = [k for k in keywords if k.lower() in str(actual_output).lower()]
            score = 1.0 if found else 0.0
            reasoning = f"Found keywords: {found}" if found else "No required keywords found."

        elif func_name == "json_validity":
            try:
                # Assume actual_output might be a json string or dict
                if isinstance(actual_output, str):
                    import json
                    json.loads(actual_output)
                score = 1.0
                reasoning = "Valid JSON."
            except:
                score = 0.0
                reasoning = "Invalid JSON format."
        
        else:
            score = 0.0
            reasoning = f"Unknown local function: {func_name}"

        return {
            "metric": self.config.name,
            "score": score,
            "passed": score >= (self.config.pass_threshold or 0),
            "reasoning": reasoning
        }

class HumanPlaceholderEvaluator(BaseEvaluator):
    """
    Placeholder for Human Evaluation.
    In a real system, this might create a task in a labeling tool.
    """
    def evaluate(self, input_data: Any, actual_output: Any, expected_output: Any) -> Dict[str, Any]:
        print(f"  [Human] Queuing for manual review...")
        return {
            "metric": self.config.name,
            "score": None, # Score is pending
            "passed": False, # Default to False or Pending
            "reasoning": "Queued for human expert review."
        }

class CustomEvaluator(BaseEvaluator):
    """
    Mock implementation for specific custom evaluators.
    """
    def evaluate(self, input_data: Any, actual_output: Any, expected_output: Any) -> Dict[str, Any]:
        target = self.config.target
        print(f"  [Custom] Running {target}...")
        
        if target == "ProductRecommendation":
            # Mock metrics for Product Recommendation
            return {
                "metric": "ProductRecommendation",
                "score": round(random.uniform(0.7, 1.0), 2),
                "passed": True,
                "reasoning": "Mock Product Recommendation logic.",
                "details": {
                    "precision": round(random.uniform(0.8, 1.0), 2),
                    "recall": round(random.uniform(0.7, 0.9), 2),
                    "diversity": round(random.uniform(0.5, 1.0), 2)
                }
            }
        elif target == "ApprovalEvaluator":
            # Mock metrics for Approval
            return {
                "metric": "ApprovalEvaluator",
                "score": round(random.uniform(0.8, 1.0), 2),
                "passed": True,
                "reasoning": "Mock Approval logic.",
                "details": {
                    "accuracy": round(random.uniform(0.9, 1.0), 2),
                    "latency_ms": random.randint(50, 200)
                }
            }
        else:
            return {
                "metric": target,
                "score": 0.0,
                "passed": False,
                "reasoning": f"Unknown custom evaluator: {target}"
            }

class EvaluatorFactory:
    @staticmethod
    def create(config) -> BaseEvaluator:
        if config.type == "azure-builtin":
            return AzureBuiltInEvaluator(config)
        elif config.type == "custom":
            return CustomEvaluator(config)
        elif config.type == "custom-service":
            # Fallback or remove if not used
            return CustomEvaluator(config) 
        elif config.type == "local-function":
            return LocalFunctionEvaluator(config)
        elif config.type == "human-placeholder":
            return HumanPlaceholderEvaluator(config)
        else:
            raise ValueError(f"Unknown evaluator type: {config.type}")
