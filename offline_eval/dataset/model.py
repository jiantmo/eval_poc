from typing import Any, Dict, Optional
from dataclasses import dataclass
import json

@dataclass
class EvalRecord:
    input: Any
    expected: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvalRecord':
        return cls(
            input=data.get("input"),
            expected=data.get("expected"),
            metadata=data.get("metadata")
        )

def load_dataset(file_path: str) -> list[EvalRecord]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("Dataset file must contain a list of records")
        
    return [EvalRecord.from_dict(item) for item in data]
