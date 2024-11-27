from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class DownloadOption:
    """Represents a document download option"""
    mime_type: str
    download_url: str
    page_count: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'DownloadOption':
        return cls(
            mime_type=data['mimeTypeIdentifier'],
            download_url=data['downloadUrl'],
            page_count=data.get('pageTotalQuantity')
        )

@dataclass
class PatentDocument:
    """Represents a single patent document"""
    application_number: str
    official_date: datetime
    document_identifier: str
    document_code: str
    document_description: str
    direction_category: str
    download_options: List[DownloadOption] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'PatentDocument':
        return cls(
            application_number=data['applicationNumberText'],
            official_date=datetime.fromisoformat(data['officialDate'].replace('Z', '+00:00')),
            document_identifier=data['documentIdentifier'],
            document_code=data['documentCode'],
            document_description=data['documentCodeDescriptionText'],
            direction_category=data['directionCategory'],
            download_options=[DownloadOption.from_dict(opt) for opt in data.get('downloadOptionBag', [])]
        )

@dataclass
class PatentDocumentCollection:
    """Collection of patent documents"""
    documents: List[PatentDocument] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'PatentDocumentCollection':
        return cls(
            documents=[PatentDocument.from_dict(doc) for doc in data.get('documentBag', [])]
        )
