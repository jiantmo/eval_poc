import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field

DATA_DIR = "runs"
RUNS_FILE = os.path.join(DATA_DIR, "runs.json")
DATASETS_FILE = os.path.join(DATA_DIR, "datasets.json")
ENVIRONMENTS_FILE = os.path.join(DATA_DIR, "environments.json")
EVALUATORS_FILE = os.path.join(DATA_DIR, "evaluators.json")

@dataclass
class RunRecord:
    id: str
    name: str
    environment: str
    agent: str
    dataset: str
    status: str  # "Running", "Succeeded", "Failed"
    created_at: str
    duration: str = "0s"
    pass_rate: float = 0.0
    total_records: int = 0
    results: List[Dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RunRecord':
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class DatasetRecord:
    id: str
    name: str
    description: str
    file_path: str
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'DatasetRecord':
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class EnvironmentRecord:
    id: str
    name: str # Display name
    env_id: str # Aurora ID
    env_version: str
    agent_name: str
    api_endpoint: str
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'EnvironmentRecord':
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class EvaluatorRecord:
    id: str
    name: str
    category: str
    type: str
    target: str
    pass_threshold: float
    parameters: Dict
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'EvaluatorRecord':
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return asdict(self)

class DataStore:
    def __init__(self):
        self._ensure_dir()
        self._ensure_file(RUNS_FILE)
        self._ensure_file(DATASETS_FILE)
        self._ensure_file(ENVIRONMENTS_FILE)
        self._ensure_file(EVALUATORS_FILE)
        
        # Seed initial data if empty
        self._seed_defaults()

    def _ensure_dir(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def _ensure_file(self, path):
        if not os.path.exists(path):
            with open(path, 'w') as f:
                json.dump([], f)

    def _load(self, path, cls):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return [cls.from_dict(item) for item in data]
        except Exception:
            return []

    def _save(self, path, items):
        with open(path, 'w') as f:
            json.dump([item.to_dict() for item in items], f, indent=2)

    def _seed_defaults(self):
        # Seed Datasets
        if not self.list_datasets():
            self.save_dataset(DatasetRecord(
                id="default-sample",
                name="Sample Records",
                description="Default sample dataset",
                file_path="dataset/sample_records.json",
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        # Seed Environments
        if not self.list_environments():
            self.save_environment(EnvironmentRecord(
                id="default-env",
                name="Aurora Test Env 001",
                env_id="aurora-test-001",
                env_version="10.0.38",
                agent_name="finance-advisor-bot",
                api_endpoint="http://mock",
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

        # Seed Evaluators (Load from sample_eval_config.json if exists, else manual seed)
        if not self.list_evaluators():
            try:
                with open("evaluation/sample_eval_config.json", "r") as f:
                    data = json.load(f)
                    for e in data.get("evaluators", []):
                        self.save_evaluator(EvaluatorRecord(
                            id=e["name"].lower().replace(" ", "-"),
                            name=e["name"],
                            category=e.get("category", "Uncategorized"),
                            type=e["type"],
                            target=e["target"],
                            pass_threshold=e.get("pass_threshold", 0.0),
                            parameters=e.get("parameters", {}),
                            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ))
            except:
                pass

    # --- Runs ---
    def list_runs(self) -> List[RunRecord]:
        runs = self._load(RUNS_FILE, RunRecord)
        return sorted(runs, key=lambda x: x.created_at, reverse=True)

    def save_run(self, run: RunRecord):
        runs = self.list_runs()
        existing_index = next((i for i, r in enumerate(runs) if r.id == run.id), -1)
        if existing_index >= 0:
            runs[existing_index] = run
        else:
            runs.append(run)
        self._save(RUNS_FILE, runs)

    # --- Datasets ---
    def list_datasets(self) -> List[DatasetRecord]:
        return self._load(DATASETS_FILE, DatasetRecord)

    def save_dataset(self, dataset: DatasetRecord):
        items = self.list_datasets()
        items.append(dataset)
        self._save(DATASETS_FILE, items)

    # --- Environments ---
    def list_environments(self) -> List[EnvironmentRecord]:
        return self._load(ENVIRONMENTS_FILE, EnvironmentRecord)

    def save_environment(self, env: EnvironmentRecord):
        items = self.list_environments()
        items.append(env)
        self._save(ENVIRONMENTS_FILE, items)

    # --- Evaluators ---
    def list_evaluators(self) -> List[EvaluatorRecord]:
        return self._load(EVALUATORS_FILE, EvaluatorRecord)

    def save_evaluator(self, evaluator: EvaluatorRecord):
        items = self.list_evaluators()
        items.append(evaluator)
        self._save(EVALUATORS_FILE, items)
