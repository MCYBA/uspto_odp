from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date

@dataclass
class Address:
    """Represents an address"""
    line1: str
    city: str
    geographic_region: str
    line2: Optional[str] = None
    line3: Optional[str] = None
    postal_code: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Address':
        return cls(
            line1=data.get('addressLineOneText', ''),
            line2=data.get('addressLineTwoText'),
            line3=data.get('addressLineThreeText'),
            city=data.get('cityName', ''),
            geographic_region=data.get('geographicRegionCode', ''),
            postal_code=data.get('postalCode')
        )

@dataclass
class Assignor:
    """Represents an assignor"""
    name: str
    execution_date: date

    @classmethod
    def from_dict(cls, data: dict) -> 'Assignor':
        return cls(
            name=data.get('assignorName', ''),
            execution_date=date.fromisoformat(data.get('executionDate', '1900-01-01'))
        )

@dataclass
class Assignee:
    """Represents an assignee"""
    name: str
    address: Address

    @classmethod
    def from_dict(cls, data: dict) -> 'Assignee':
        return cls(
            name=data.get('assigneeNameText', ''),
            address=Address.from_dict(data.get('assigneeAddress', {}))
        )

@dataclass
class Correspondent:
    """Represents a correspondent"""
    name: str
    address: Address

    @classmethod
    def from_dict(cls, data: dict) -> 'Correspondent':
        address_data = {
            'addressLineOneText': data.get('addressLineOneText', ''),
            'addressLineTwoText': data.get('addressLineTwoText'),
            'addressLineThreeText': data.get('addressLineThreeText'),
            'cityName': data.get('addressLineThreeText', '').split(',')[0] if data.get('addressLineThreeText') else '',
            'geographicRegionCode': ''
        }
        return cls(
            name=data.get('correspondentNameText', ''),
            address=Address.from_dict(address_data)
        )

@dataclass
class Assignment:
    """Represents a single assignment"""
    received_date: date
    recorded_date: date
    mailed_date: date
    reel_number: int
    frame_number: int
    page_number: int
    reel_frame: str
    conveyance_text: str
    assignors: List[Assignor] = field(default_factory=list)
    assignees: List[Assignee] = field(default_factory=list)
    correspondents: List[Correspondent] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'Assignment':
        return cls(
            received_date=date.fromisoformat(data.get('assignmentReceivedDate', '1900-01-01')),
            recorded_date=date.fromisoformat(data.get('assignmentRecordedDate', '1900-01-01')),
            mailed_date=date.fromisoformat(data.get('assignmentMailedDate', '1900-01-01')),
            reel_number=int(data.get('reelNumber', 0)),
            frame_number=int(data.get('frameNumber', 0)),
            page_number=int(data.get('pageNumber', 0)),
            reel_frame=data.get('reelNumber/frameNumber', ''),
            conveyance_text=data.get('conveyanceText', ''),
            assignors=[Assignor.from_dict(a) for a in data.get('assignorBag', [])],
            assignees=[Assignee.from_dict(a) for a in data.get('assigneeBag', [])],
            correspondents=[Correspondent.from_dict(c) for c in data.get('correspondenceAddressBag', [])]
        )

@dataclass
class ApplicationAssignment:
    """Represents assignments for a patent application"""
    application_number: str
    assignments: List[Assignment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'ApplicationAssignment':
        return cls(
            application_number=data.get('applicationNumberText', ''),
            assignments=[Assignment.from_dict(a) for a in data.get('assignmentBag', [])]
        )

@dataclass
class AssignmentCollection:
    """Collection of assignment data"""
    count: int
    assignments: List[ApplicationAssignment] = field(default_factory=list)
    request_identifier: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'AssignmentCollection':
        return cls(
            count=data.get('count', 0),
            assignments=[ApplicationAssignment.from_dict(pw) 
                        for pw in data.get('patentFileWrapperDataBag', [])],
            request_identifier=data.get('requestIdentifier')
        )
