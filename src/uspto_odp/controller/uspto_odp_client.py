'''
MIT License

Copyright (c) 2024 Ken Thompson, https://github.com/KennethThompson, all rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from dataclasses import dataclass
from typing import Optional, Union
import aiohttp
import logging
from uspto_odp.models.patent_file_wrapper import PatentFileWrapper
from uspto_odp.models.patent_documents import PatentDocumentCollection, PatentDocument
from uspto_odp.models.patent_continuity import ContinuityCollection
from uspto_odp.models.foreign_priority import ForeignPriorityCollection
from uspto_odp.models.patent_transactions import TransactionCollection
from uspto_odp.models.patent_assignment import AssignmentCollection
import os
try:
    from enum import StrEnum  # Python 3.11+
except ImportError:
    from strenum import StrEnum  # Python 3.9+

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class USPTOError(Exception):
    """Exception for USPTO API errors."""
    def __init__(self, code: int, error: str, error_details: Optional[str] = None, request_identifier: Optional[str] = None):
        self.code = code
        self.error = error
        self.error_details = error_details
        self.request_identifier = request_identifier
        super().__init__(f"{code}: {error} - {error_details or 'No details provided'}")

    @classmethod
    def from_dict(cls, data: dict, status_code: int) -> 'USPTOError':
        default_messages = {
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error"
        }
        return cls(
            code=data.get('code', status_code),
            error=data.get('error', default_messages.get(status_code, "Unknown Error")),
            error_details=data.get('errorDetails') or data.get('errorDetailed'),
            request_identifier=data.get('requestIdentifier')
        )

class USPTOClient:
    """Async client for USPTO Patent Application API"""
    
    BASE_URL = "https://beta-api.uspto.gov/api/v1/patent/applications"

    def __init__(self, api_key: str, session: Optional[aiohttp.ClientSession] = None):
        self.API_KEY = api_key
        self.headers = {
            "accept": "application/json",
            "X-API-KEY": self.API_KEY
        }
        self.session = session or aiohttp.ClientSession()

    async def _handle_response(self, response, parse_func):
        try:
            data = await response.json()
        except Exception:
            data = {}
        
        if response.status == 200:
            return parse_func(data)
        
        error = USPTOError.from_dict(data, response.status)
        self._log_error(error)
        raise error

    def _log_error(self, error: USPTOError):
        logger.error(
            f"USPTO API Error: {error.code}\n"
            f"Error Message: {error.error}\n"
            f"Details: {error.error_details or 'No details provided'}\n"
            f"Request ID: {error.request_identifier or 'No request ID provided'}"
        )

    async def get_patent_wrapper(self, serial_number: str) -> PatentFileWrapper:
        url = f"{self.BASE_URL}/{serial_number}"
        async with self.session.get(url, headers=self.headers) as response:
            return await self._handle_response(response, PatentFileWrapper.parse_response)

    async def get_patent_documents(self, serial_number: str) -> PatentDocumentCollection:
        url = f"{self.BASE_URL}/{serial_number}/documents"
        async with self.session.get(url, headers=self.headers) as response:
            return await self._handle_response(response, PatentDocumentCollection.from_dict)

    async def download_document(
        self, 
        document: PatentDocument, 
        save_path: str,
        filename: Optional[str] = None,
        mime_type: str = "PDF"
    ) -> str:
        if not os.path.exists(save_path):
            raise FileNotFoundError(f"Save path does not exist: {save_path}")
        if not os.access(save_path, os.W_OK):
            raise PermissionError(f"Save path is not writable: {save_path}")
            
        download_option = next(
            (opt for opt in document.download_options if opt.mime_type == mime_type),
            None
        )
        
        if not download_option:
            available_types = [opt.mime_type for opt in document.download_options]
            raise ValueError(
                f"Mime type '{mime_type}' not available for this document. "
                f"Available types: {', '.join(available_types)}"
            )
            
        if not filename:
            extension = ".pdf" if mime_type == "PDF" else ".doc" if mime_type == "MS_WORD" else ".xml"
            filename = f"{document.application_number}_{document.document_code}_{document.document_identifier}{extension}"
            
        full_path = os.path.join(save_path, filename)
        
        async with self.session.get(download_option.download_url, headers=self.headers) as response:
            if response.status != 200:
                raise Exception(f"Download failed with status {response.status}")
                
            with open(full_path, 'wb') as f:
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                        
        logger.info(
            f"Successfully downloaded document {document.document_identifier} "
            f"({mime_type}) to {full_path}"
        )
        
        return full_path

    async def get_patent_continuity(self, serial_number: str) -> ContinuityCollection:
        url = f"{self.BASE_URL}/{serial_number}/continuity"
        async with self.session.get(url, headers=self.headers) as response:
            return await self._handle_response(response, ContinuityCollection.from_dict)

    async def get_foreign_priority(self, serial_number: str) -> ForeignPriorityCollection:
        url = f"{self.BASE_URL}/{serial_number}/foreign-priority"
        async with self.session.get(url, headers=self.headers) as response:
            return await self._handle_response(response, ForeignPriorityCollection.from_dict)

    async def get_patent_transactions(self, serial_number: str) -> TransactionCollection:
        url = f"{self.BASE_URL}/{serial_number}/transactions"
        async with self.session.get(url, headers=self.headers) as response:
            return await self._handle_response(response, TransactionCollection.from_dict)

    async def get_patent_assignments(self, serial_number: str) -> AssignmentCollection:
        url = f"{self.BASE_URL}/{serial_number}/assignment"
        async with self.session.get(url, headers=self.headers) as response:
            return await self._handle_response(response, AssignmentCollection.from_dict)
