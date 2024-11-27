from dataclasses import dataclass, field
from typing import List
from datetime import date

@dataclass
class ForeignPriority:
    """Represents a foreign priority claim"""
    office_name: str
    filing_date: date
    application_number: str

    @classmethod
    def from_dict(cls, data: dict) -> 'ForeignPriority':
        return cls(
            office_name=data.get('ipOfficeName', ''),
            filing_date=date.fromisoformat(data.get('filingDate', '1900-01-01')),
            application_number=data.get('applicationNumberText', '')
        )

@dataclass
class ForeignPriorityData:
    """Represents foreign priority data for a patent application"""
    application_number: str
    foreign_priorities: List[ForeignPriority] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'ForeignPriorityData':
        return cls(
            application_number=data.get('applicationNumberText', ''),
            foreign_priorities=[
                ForeignPriority.from_dict(fp) 
                for fp in data.get('foreignPriorityBag', [])
            ]
        )

@dataclass
class ForeignPriorityCollection:
    """Collection of foreign priority data"""
    count: int
    priorities: List[ForeignPriorityData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'ForeignPriorityCollection':
        return cls(
            count=data.get('count', 0),
            priorities=[
                ForeignPriorityData.from_dict(pw) 
                for pw in data.get('patentFileWrapperDataBag', [])
            ]
        )
