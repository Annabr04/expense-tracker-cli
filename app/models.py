from dataclasses import dataclass
from typing import Optional


@dataclass
class Expense:
    id: int
    amount: float
    category: str
    description: Optional[str]
    date: str
    created_at: str
