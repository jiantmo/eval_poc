from typing import List, Dict, Any
from dataclasses import dataclass
from .config import EvaluationSuiteConfig
from .evaluators import EvaluatorFactory
from runner import ExecutionResult

@dataclass
class EvalResult:
    execution_result: ExecutionResult
    metrics: Dict[str, Any]
    passed: bool

class EvaluationEngine:
    def __init__(self, suite_config: EvaluationSuiteConfig):
        self.config = suite_config
        self.evaluators = [EvaluatorFactory.create(cfg) for cfg in suite_config.evaluators]

    def evaluate_run(self, execution_results: List[ExecutionResult]) -> List[EvalResult]:
        final_results = []
        print(f"Starting evaluation suite: {self.config.suite_name}")

        for exec_res in execution_results:
            if exec_res.error:
                print(f"Skipping evaluation for failed execution: {exec_res.error}")
                continue

            record_metrics = {}
            all_passed = True

            print(f"Evaluating record input: {exec_res.record.input}...")
            
            for evaluator in self.evaluators:
                # Extract relevant data for evaluation
                # Note: Some metrics need 'context' or 'ground_truth' which might be in metadata or expected
                input_val = exec_res.record.input
                actual_val = exec_res.actual_output
                expected_val = exec_res.record.expected

                result = evaluator.evaluate(input_val, actual_val, expected_val)
                
                record_metrics[evaluator.config.name] = result
                if not result.get("passed", True):
                    all_passed = False
            
            final_results.append(EvalResult(
                execution_result=exec_res,
                metrics=record_metrics,
                passed=all_passed
            ))
            
        return final_results
