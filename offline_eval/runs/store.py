import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field

# Use absolute path for DB to avoid issues with CWD
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline_eval.db")

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
    # New fields for relational linking
    dataset_id: Optional[str] = None
    environment_id: Optional[str] = None
    evaluator_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RunRecord':
        # Handle JSON fields if they come from DB as strings
        if isinstance(data.get('results'), str):
            try:
                data['results'] = json.loads(data['results'])
            except:
                data['results'] = []
        if isinstance(data.get('evaluator_ids'), str):
            try:
                data['evaluator_ids'] = json.loads(data['evaluator_ids'])
            except:
                data['evaluator_ids'] = []
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class DatasetRecord:
    id: str
    name: str
    description: str
    created_at: str
    content: List[Dict] = field(default_factory=list)
    file_path: Optional[str] = None # Keep for backward compat or reference

    @classmethod
    def from_dict(cls, data: Dict) -> 'DatasetRecord':
        if isinstance(data.get('content'), str):
            try:
                data['content'] = json.loads(data['content'])
            except:
                data['content'] = []
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
        if isinstance(data.get('parameters'), str):
            try:
                data['parameters'] = json.loads(data['parameters'])
            except:
                data['parameters'] = {}
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class TestSuiteRecord:
    id: str
    name: str
    description: str
    dataset_id: str
    environment_id: str
    evaluator_ids: List[str]
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestSuiteRecord':
        if isinstance(data.get('evaluator_ids'), str):
            try:
                data['evaluator_ids'] = json.loads(data['evaluator_ids'])
            except:
                data['evaluator_ids'] = []
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return asdict(self)

class DataStore:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._seed_defaults()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            content TEXT,
            file_path TEXT,
            created_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS environments (
            id TEXT PRIMARY KEY,
            name TEXT,
            env_id TEXT,
            env_version TEXT,
            agent_name TEXT,
            api_endpoint TEXT,
            created_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluators (
            id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            type TEXT,
            target TEXT,
            pass_threshold REAL,
            parameters TEXT,
            created_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_suites (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            dataset_id TEXT,
            environment_id TEXT,
            evaluator_ids TEXT,
            created_at TEXT,
            FOREIGN KEY(dataset_id) REFERENCES datasets(id),
            FOREIGN KEY(environment_id) REFERENCES environments(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            name TEXT,
            environment TEXT,
            agent TEXT,
            dataset TEXT,
            status TEXT,
            created_at TEXT,
            duration TEXT,
            pass_rate REAL,
            total_records INTEGER,
            results TEXT,
            dataset_id TEXT,
            environment_id TEXT,
            evaluator_ids TEXT,
            FOREIGN KEY(dataset_id) REFERENCES datasets(id),
            FOREIGN KEY(environment_id) REFERENCES environments(id)
        )
        """)
        
        self.conn.commit()

    def _seed_defaults(self):
        # Seed Datasets
        if not self.list_datasets():
            content = []
            try:
                # Try to find the file relative to the current working directory or the file location
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                file_path = os.path.join(base_path, "dataset", "sample_records.json")
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding='utf-8') as f:
                        content = json.load(f)
            except Exception as e:
                print(f"Error seeding dataset: {e}")
                pass
                
            self.save_dataset(DatasetRecord(
                id="default-sample",
                name="Sample Records",
                description="Default sample dataset",
                file_path="dataset/sample_records.json",
                content=content,
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

        # Seed Evaluators
        if not self.list_evaluators():
            try:
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                file_path = os.path.join(base_path, "evaluation", "sample_eval_config.json")
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding='utf-8') as f:
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
            except Exception as e:
                print(f"Error seeding evaluators: {e}")
                pass

    # --- Runs ---
    def list_runs(self) -> List[RunRecord]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM runs ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [RunRecord.from_dict(dict(row)) for row in rows]

    def save_run(self, run: RunRecord):
        cursor = self.conn.cursor()
        # Check if exists
        cursor.execute("SELECT 1 FROM runs WHERE id = ?", (run.id,))
        exists = cursor.fetchone()
        
        data = run.to_dict()
        data['results'] = json.dumps(data['results'])
        data['evaluator_ids'] = json.dumps(data['evaluator_ids'])
        
        if exists:
            cursor.execute("""
                UPDATE runs SET 
                    name=?, environment=?, agent=?, dataset=?, status=?, 
                    created_at=?, duration=?, pass_rate=?, total_records=?, 
                    results=?, dataset_id=?, environment_id=?, evaluator_ids=?
                WHERE id=?
            """, (
                data['name'], data['environment'], data['agent'], data['dataset'], data['status'],
                data['created_at'], data['duration'], data['pass_rate'], data['total_records'],
                data['results'], data['dataset_id'], data['environment_id'], data['evaluator_ids'],
                data['id']
            ))
        else:
            cursor.execute("""
                INSERT INTO runs (
                    id, name, environment, agent, dataset, status, 
                    created_at, duration, pass_rate, total_records, 
                    results, dataset_id, environment_id, evaluator_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['id'], data['name'], data['environment'], data['agent'], data['dataset'], data['status'],
                data['created_at'], data['duration'], data['pass_rate'], data['total_records'],
                data['results'], data['dataset_id'], data['environment_id'], data['evaluator_ids']
            ))
        self.conn.commit()

    # --- Datasets ---
    def list_datasets(self) -> List[DatasetRecord]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM datasets")
        rows = cursor.fetchall()
        return [DatasetRecord.from_dict(dict(row)) for row in rows]

    def save_dataset(self, dataset: DatasetRecord):
        cursor = self.conn.cursor()
        data = dataset.to_dict()
        data['content'] = json.dumps(data['content'])
        
        cursor.execute("SELECT 1 FROM datasets WHERE id = ?", (dataset.id,))
        if cursor.fetchone():
             cursor.execute("""
                UPDATE datasets SET name=?, description=?, content=?, file_path=?, created_at=? WHERE id=?
            """, (data['name'], data['description'], data['content'], data['file_path'], data['created_at'], data['id']))
        else:
            cursor.execute("""
                INSERT INTO datasets (id, name, description, content, file_path, created_at) VALUES (?, ?, ?, ?, ?, ?)
            """, (data['id'], data['name'], data['description'], data['content'], data['file_path'], data['created_at']))
        self.conn.commit()

    # --- Environments ---
    def list_environments(self) -> List[EnvironmentRecord]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM environments")
        rows = cursor.fetchall()
        return [EnvironmentRecord.from_dict(dict(row)) for row in rows]

    def save_environment(self, env: EnvironmentRecord):
        cursor = self.conn.cursor()
        data = env.to_dict()
        
        cursor.execute("SELECT 1 FROM environments WHERE id = ?", (env.id,))
        if cursor.fetchone():
             cursor.execute("""
                UPDATE environments SET name=?, env_id=?, env_version=?, agent_name=?, api_endpoint=?, created_at=? WHERE id=?
            """, (data['name'], data['env_id'], data['env_version'], data['agent_name'], data['api_endpoint'], data['created_at'], data['id']))
        else:
            cursor.execute("""
                INSERT INTO environments (id, name, env_id, env_version, agent_name, api_endpoint, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data['id'], data['name'], data['env_id'], data['env_version'], data['agent_name'], data['api_endpoint'], data['created_at']))
        self.conn.commit()

    # --- Evaluators ---
    def list_evaluators(self) -> List[EvaluatorRecord]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM evaluators")
        rows = cursor.fetchall()
        return [EvaluatorRecord.from_dict(dict(row)) for row in rows]

    def save_evaluator(self, evaluator: EvaluatorRecord):
        cursor = self.conn.cursor()
        data = evaluator.to_dict()
        data['parameters'] = json.dumps(data['parameters'])
        
        cursor.execute("SELECT 1 FROM evaluators WHERE id = ?", (evaluator.id,))
        if cursor.fetchone():
             cursor.execute("""
                UPDATE evaluators SET name=?, category=?, type=?, target=?, pass_threshold=?, parameters=?, created_at=? WHERE id=?
            """, (data['name'], data['category'], data['type'], data['target'], data['pass_threshold'], data['parameters'], data['created_at'], data['id']))
        else:
            cursor.execute("""
                INSERT INTO evaluators (id, name, category, type, target, pass_threshold, parameters, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data['id'], data['name'], data['category'], data['type'], data['target'], data['pass_threshold'], data['parameters'], data['created_at']))
        self.conn.commit()

    # --- Test Suites ---
    def list_test_suites(self) -> List[TestSuiteRecord]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM test_suites")
        rows = cursor.fetchall()
        return [TestSuiteRecord.from_dict(dict(row)) for row in rows]

    def save_test_suite(self, suite: TestSuiteRecord):
        cursor = self.conn.cursor()
        data = suite.to_dict()
        data['evaluator_ids'] = json.dumps(data['evaluator_ids'])
        
        cursor.execute("SELECT 1 FROM test_suites WHERE id = ?", (suite.id,))
        if cursor.fetchone():
             cursor.execute("""
                UPDATE test_suites SET name=?, description=?, dataset_id=?, environment_id=?, evaluator_ids=?, created_at=? WHERE id=?
            """, (data['name'], data['description'], data['dataset_id'], data['environment_id'], data['evaluator_ids'], data['created_at'], data['id']))
        else:
            cursor.execute("""
                INSERT INTO test_suites (id, name, description, dataset_id, environment_id, evaluator_ids, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data['id'], data['name'], data['description'], data['dataset_id'], data['environment_id'], data['evaluator_ids'], data['created_at']))
        self.conn.commit()
