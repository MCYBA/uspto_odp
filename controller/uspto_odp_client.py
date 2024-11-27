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
from models.patent_file_wrapper import PatentFileWrapper
from models.patent_documents import PatentDocumentCollection, PatentDocument
from models.patent_continuity import ContinuityCollection
from models.foreign_priority import ForeignPriorityCollection
from models.patent_transactions import TransactionCollection
from models.patent_assignment import AssignmentCollection
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class USPTOError:
    """Represents USPTO API error responses"""
    code: int
    error: str
    error_details: Optional[str] = None
    request_identifier: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict, status_code: int) -> 'USPTOError':
        """
        Create error object from response data with fallbacks for missing fields
        
        Args:
            data: Response JSON data
            status_code: HTTP status code from response
        """
        # Map status codes to default error messages
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

    def __init__(self, api_key: str):
        self.API_KEY = api_key
        self.headers = {
            "accept": "application/json",
            "X-API-KEY": self.API_KEY
        }

    async def get_patent_wrapper(self, serial_number: str) -> Union[PatentFileWrapper, USPTOError]:
        """
        Fetches patent wrapper data for a given serial number
        
        Args:
            serial_number: The patent application serial number
            
        Returns:
            Either a PatentFileWrapper object or USPTOError depending on the response
        """
        url = f"{self.BASE_URL}/{serial_number}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                try:
                    data = await response.json()
                except Exception:
                    # Handle case where response isn't valid JSON
                    data = {}
                
                if response.status == 200:
                    return PatentFileWrapper.parse_response(data)
                
                # Map status codes to human-readable descriptions
                status_descriptions = {
                    400: "Bad Request - Invalid request parameters",
                    403: "Forbidden - Authentication failed or access denied",
                    404: "Not Found - Patent application doesn't exist",
                    500: "Internal Server Error - USPTO API issue"
                }
                
                # Handle error responses
                error = USPTOError.from_dict(data, response.status)
                status_desc = status_descriptions.get(response.status, "Unknown Error")
                
                logger.error(
                    f"USPTO API Error: {error.code} - {status_desc}\n"
                    f"Error Message: {error.error}\n"
                    f"Details: {error.error_details or 'No details provided'}\n"
                    f"Request ID: {error.request_identifier or 'No request ID provided'}"
                )
                return error

    async def get_patent_documents(self, serial_number: str) -> Union[PatentDocumentCollection, USPTOError]:
        """
        Fetches patent documents for a given serial number
        
        Args:
            serial_number: The patent application serial number
            
        Returns:
            Either a PatentDocumentCollection object or USPTOError depending on the response
        """
        url = f"{self.BASE_URL}/{serial_number}/documents"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                try:
                    data = await response.json()
                except Exception:
                    # Handle case where response isn't valid JSON
                    data = {}
                
                if response.status == 200:
                    return PatentDocumentCollection.from_dict(data)
                
                # Handle error responses
                error = USPTOError.from_dict(data, response.status)
                logger.error(
                    f"USPTO API Error: {error.code}\n"
                    f"Error Message: {error.error}\n"
                    f"Details: {error.error_details or 'No details provided'}\n"
                    f"Request ID: {error.request_identifier or 'No request ID provided'}"
                )
                return error

    async def download_document(
        self, 
        document: PatentDocument, 
        save_path: str,
        filename: Optional[str] = None,
        mime_type: str = "PDF"
    ) -> str:
        """
        Downloads a patent document and saves it to the specified path
        
        Args:
            document: PatentDocument object containing download information
            save_path: Directory path where the file should be saved
            filename: Optional custom filename. If not provided, generates from document properties
            mime_type: Desired mime type (defaults to PDF)
            
        Returns:
            Path to the downloaded file
            
        Raises:
            ValueError: If the requested mime type is not available for this document
            FileNotFoundError: If the save path doesn't exist
            PermissionError: If the save path is not writable
            Exception: For other download/save errors
        """
        # Verify save path exists and is writable
        if not os.path.exists(save_path):
            raise FileNotFoundError(f"Save path does not exist: {save_path}")
        if not os.access(save_path, os.W_OK):
            raise PermissionError(f"Save path is not writable: {save_path}")
            
        # Find matching download option for requested mime type
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
            
        # Generate default filename if none provided
        if not filename:
            extension = ".pdf" if mime_type == "PDF" else ".doc" if mime_type == "MS_WORD" else ".xml"
            filename = f"{document.application_number}_{document.document_code}_{document.document_identifier}{extension}"
            
        full_path = os.path.join(save_path, filename)
        
        # Download the file
        async with aiohttp.ClientSession() as session:
            async with session.get(download_option.download_url, headers=self.headers) as response:
                if response.status != 200:
                    raise Exception(f"Download failed with status {response.status}")
                
                # Save the file
                with open(full_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        f.write(chunk)
                        
        logger.info(
            f"Successfully downloaded document {document.document_identifier} "
            f"({mime_type}) to {full_path}"
        )
        
        return full_path

    async def get_patent_continuity(self, serial_number: str) -> Union[ContinuityCollection, USPTOError]:
        """
        Fetches continuity data for a given patent application
        
        Args:
            serial_number: The patent application serial number
            
        Returns:
            Either a ContinuityCollection object or USPTOError depending on the response
        """
        url = f"{self.BASE_URL}/{serial_number}/continuity"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                try:
                    data = await response.json()
                except Exception:
                    # Handle case where response isn't valid JSON
                    data = {}
                
                if response.status == 200:
                    return ContinuityCollection.from_dict(data)
                
                # Handle error responses
                error = USPTOError.from_dict(data, response.status)
                logger.error(
                    f"USPTO API Error: {error.code}\n"
                    f"Error Message: {error.error}\n"
                    f"Details: {error.error_details or 'No details provided'}\n"
                    f"Request ID: {error.request_identifier or 'No request ID provided'}"
                )
                return error

    async def get_foreign_priority(self, serial_number: str) -> Union[ForeignPriorityCollection, USPTOError]:
        """
        Fetches foreign priority data for a given patent application
        
        Args:
            serial_number: The patent application serial number
            
        Returns:
            Either a ForeignPriorityCollection object or USPTOError depending on the response
        """
        url = f"{self.BASE_URL}/{serial_number}/foreign-priority"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                try:
                    data = await response.json()
                except Exception:
                    # Handle case where response isn't valid JSON
                    data = {}
                
                if response.status == 200:
                    return ForeignPriorityCollection.from_dict(data)
                
                # Handle error responses
                error = USPTOError.from_dict(data, response.status)
                logger.error(
                    f"USPTO API Error: {error.code}\n"
                    f"Error Message: {error.error}\n"
                    f"Details: {error.error_details or 'No details provided'}\n"
                    f"Request ID: {error.request_identifier or 'No request ID provided'}"
                )
                return error

    async def get_patent_transactions(self, serial_number: str) -> Union[TransactionCollection, USPTOError]:
        """
        Fetches transaction history for a given patent application
        
        Args:
            serial_number: The patent application serial number
            
        Returns:
            Either a TransactionCollection object or USPTOError depending on the response
        """
        url = f"{self.BASE_URL}/{serial_number}/transactions"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                try:
                    data = await response.json()
                except Exception:
                    # Handle case where response isn't valid JSON
                    data = {}
                
                if response.status == 200:
                    return TransactionCollection.from_dict(data)
                
                # Handle error responses
                error = USPTOError.from_dict(data, response.status)
                logger.error(
                    f"USPTO API Error: {error.code}\n"
                    f"Error Message: {error.error}\n"
                    f"Details: {error.error_details or 'No details provided'}\n"
                    f"Request ID: {error.request_identifier or 'No request ID provided'}"
                )
                return error

    async def get_patent_assignments(self, serial_number: str) -> Union[AssignmentCollection, USPTOError]:
        """
        Fetches assignment history for a given patent application
        
        Args:
            serial_number: The patent application serial number
            
        Returns:
            Either an AssignmentCollection object or USPTOError depending on the response
        """
        url = f"{self.BASE_URL}/{serial_number}/assignment"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                try:
                    data = await response.json()
                except Exception:
                    # Handle case where response isn't valid JSON
                    data = {}
                
                if response.status == 200:
                    return AssignmentCollection.from_dict(data)
                
                # Handle error responses
                error = USPTOError.from_dict(data, response.status)
                logger.error(
                    f"USPTO API Error: {error.code}\n"
                    f"Error Message: {error.error}\n"
                    f"Details: {error.error_details or 'No details provided'}\n"
                    f"Request ID: {error.request_identifier or 'No request ID provided'}"
                )
                return error
