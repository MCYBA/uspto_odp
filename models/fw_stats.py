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
from datetime import datetime, timedelta
from typing import List
from models.patent_file_wrapper import ApplicationMetadata, PatentFileWrapper
from models.patent_status import ApplicationStatus, ApplicationStatusDerived
from models.patent_transactions import TransactionEvent

class FileWrapperProps:
    def __init__(self, serial_number: str):
        self.serial_number = serial_number
        self.maybe_concon = False
        self.days_to_first_action = 0
        self.num_actions = 0
        self.num_oa_responses = 0
        self.num_rce = 0
        self.claim_count_at_filing = 0 # future
        self.prelim_count = 0
        self.status = ApplicationStatusDerived.UNKNOWN
        self.total_days_active = 0
        self.projected_family_expiration_data = None
        
    
def analyze_transactions(transactions: List[TransactionEvent], fw_props: FileWrapperProps):
    # Sort transactions by date (earliest first)
    sorted_events = sorted(transactions, key=lambda x: x.event_date)
    
    # Initialize tracking variables
    earliest_date = sorted_events[0].event_date
    first_oa_date = None
    latest_oa_date = None
    latest_rejection = None
    rejection_count = 0
    #rce_count = 0
    has_allowance = False
    is_abandoned = False
    
    # Traverse events to gather metrics
    for event in sorted_events:
        # Track first office action date
        if not first_oa_date and event.event_code in ['MCTNF', 'MCTFR']:
            first_oa_date = event.event_date
            fw_props.days_to_first_action = (first_oa_date - earliest_date).days
        
        # Track latest rejection
        if event.event_code in ['MCTNF', 'MCTFR']:
            rejection_count += 1
            latest_oa_date = event.event_date
            latest_rejection = event
        elif event.event_code == 'RCEX':
            fw_props.num_rce += 1
        # Check for allowance
        if 'Notice of Allowance' in event.event_description_text:
            has_allowance = True
            
        # Check for abandonment
        if event.event_code.startswith('ABN') or 'Abandon' in event.event_description_text:
            is_abandoned = True
            
        # Count office action responses
        if "Response after" in event.event_description_text:
            fw_props.num_oa_responses += 1
    
    # Update FileWrapperProps
    fw_props.num_actions = rejection_count
    

    
    # Check for response within 3 months of latest rejection
    has_timely_response_to_latest_rejection = False
    response_deadline_passed = False
    if latest_rejection:
        response_deadline = latest_rejection.event_date + timedelta(days=90)
        has_timely_response_to_latest_rejection = any(
            "Response after" in event.event_description_text 
            and latest_rejection.event_date < event.event_date <= response_deadline
            for event in sorted_events
        )
        if latest_rejection.event_date + timedelta(days=90) > datetime.now().date():
            response_deadline_passed = False
        else:
            response_deadline_passed = True
        

    if has_allowance:
        # Find allowance date
        allowance_date = next(
            (e.event_date for e in sorted_events 
                if 'Notice of Allowance' in e.event_description_text),
            None
        )
        if allowance_date:
            # Calculate total days from earliest date to allowance + 90 days
            fw_props.total_days_active = (allowance_date - earliest_date).days + 90
    
    elif latest_oa_date and not has_timely_response_to_latest_rejection:
        # Calculate total days from earliest date to latest OA + 90 days
        fw_props.total_days_active = (latest_oa_date - earliest_date).days + 90
    elif latest_oa_date and has_timely_response_to_latest_rejection:
        # Fix: Convert datetime.now() to date for consistent comparison
        fw_props.total_days_active = (datetime.now().date() - earliest_date).days
    else:
        # Fix: Convert datetime.now() to date for consistent comparison
        fw_props.total_days_active = (datetime.now().date() - earliest_date).days
        
    # Set derived status
    if has_allowance:
        fw_props.status = ApplicationStatusDerived.ALLOWED
    elif latest_oa_date and not has_timely_response_to_latest_rejection:
        fw_props.status = ApplicationStatusDerived.MAYBE_ABANDONED
        fw_props.maybe_concon = True
    elif is_abandoned and fw_props.num_oa_responses == 0:
        fw_props.maybe_concon = True
    elif is_abandoned:
        fw_props.status = ApplicationStatusDerived.ABANDONED
    else:
        fw_props.status = ApplicationStatusDerived.MAYBE_PENDING
    
    print(f'{fw_props.serial_number}, earliest date = {earliest_date}, status = {fw_props.status}, days to first action = {fw_props.days_to_first_action}, total days active = {fw_props.total_days_active}, maybe concon = {fw_props.maybe_concon}, num actions = {fw_props.num_actions}, num OA responses = {fw_props.num_oa_responses}, num RCEs = {fw_props.num_rce}')
    return fw_props

def analyze_wrapper(wrapper: PatentFileWrapper):
    fw_props = FileWrapperProps(wrapper.application_number)
    fw_props = analyze_transactions(transactions=wrapper.events, fw_props=fw_props)

    
    pass