from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Expense:
    id: int
    amount: Decimal
    category: str
    description: Optional[str]
    date: str
    created_at: str
