from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date

@dataclass
class TransactionEvent:
    """Represents a single transaction event"""
    event_code: str
    event_description: str
    event_date: date

    @classmethod
    def from_dict(cls, data: dict) -> 'TransactionEvent':
        return cls(
            event_code=data.get('eventCode', ''),
            event_description=data.get('eventDescriptionText', ''),
            event_date=date.fromisoformat(data.get('eventDate', '1900-01-01'))
        )

@dataclass
class ApplicationTransactions:
    """Represents all transactions for a patent application"""
    application_number: str
    events: List[TransactionEvent] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'ApplicationTransactions':
        return cls(
            application_number=data.get('applicationNumberText', ''),
            events=[TransactionEvent.from_dict(event) 
                   for event in data.get('eventDataBag', [])]
        )

@dataclass
class TransactionCollection:
    """Collection of transaction data"""
    count: int
    transactions: List[ApplicationTransactions] = field(default_factory=list)
    request_identifier: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'TransactionCollection':
        return cls(
            count=data.get('count', 0),
            transactions=[ApplicationTransactions.from_dict(pw) 
                         for pw in data.get('patentFileWrapperDataBag', [])],
            request_identifier=data.get('requestIdentifier')
        )
