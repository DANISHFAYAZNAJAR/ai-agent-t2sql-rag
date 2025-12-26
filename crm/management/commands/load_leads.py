"""
Management command to load CRM leads from Excel file
"""
import pandas as pd
from django.core.management.base import BaseCommand
from crm.models import Lead
from datetime import datetime


def parse_budget(budget_str):
    """Parse budget string like '13,00,000' to decimal"""
    if pd.isna(budget_str) or budget_str == '':
        return None
    # Remove commas and convert to float
    try:
        return float(str(budget_str).replace(',', ''))
    except (ValueError, AttributeError):
        return None


def normalize_lead_status(status_str):
    """Normalize lead status to match model choices"""
    status_mapping = {
        'Not Connected': 'not_connected',
        'Not connected': 'not_connected',
        'Connected': 'connected',
        'connected': 'connected',
        'Visit scheduled': 'visit_scheduled',
        'visit scheduled': 'visit_scheduled',
        'Visit done not purchased': 'visit_done_not_purchased',
        'visit done not purchased': 'visit_done_not_purchased',
        'Purchased': 'purchased',
        'purchased': 'purchased',
        'Not interested': 'not_interested',
        'Not Interested': 'not_interested',
    }
    return status_mapping.get(str(status_str).strip(), 'not_connected')


class Command(BaseCommand):
    help = 'Load CRM leads from Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_file',
            type=str,
            help='Path to the Excel file containing CRM leads'
        )

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        
        self.stdout.write(f'Loading leads from {excel_file}...')
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            self.stdout.write(f'Found {len(df)} leads in Excel file')
            
            created_count = 0
            updated_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Parse data
                    lead_id = str(row['Lead ID']).strip()
                    lead_name = str(row['Lead name']).strip()
                    email = str(row['Email']).strip()
                    country_code = str(row['Country code']).strip()
                    phone = str(row['Phone']).strip()
                    project_name = str(row['Project name']).strip()
                    unit_type = str(row['Unit type']).strip()
                    min_budget = parse_budget(row.get('Min. Budget'))
                    max_budget = parse_budget(row.get('Max Budget'))
                    lead_status = normalize_lead_status(row.get('Lead status', 'Not Connected'))
                    
                    # Parse date
                    last_conversation_date = None
                    if pd.notna(row.get('Last conversation date')):
                        try:
                            if isinstance(row['Last conversation date'], datetime):
                                last_conversation_date = row['Last conversation date'].date()
                            else:
                                last_conversation_date = pd.to_datetime(row['Last conversation date']).date()
                        except:
                            pass
                    
                    last_conversation_summary = str(row.get('Last conversation summary', '')).strip()
                    
                    # Create or update lead
                    lead, created = Lead.objects.update_or_create(
                        lead_id=lead_id,
                        defaults={
                            'lead_name': lead_name,
                            'email': email,
                            'country_code': country_code,
                            'phone': phone,
                            'project_name': project_name,
                            'unit_type': unit_type,
                            'min_budget': min_budget,
                            'max_budget': max_budget,
                            'lead_status': lead_status,
                            'last_conversation_date': last_conversation_date,
                            'last_conversation_summary': last_conversation_summary,
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'Error processing row {index + 1}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully loaded leads:\n'
                    f'  Created: {created_count}\n'
                    f'  Updated: {updated_count}\n'
                    f'  Errors: {error_count}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading Excel file: {str(e)}')
            )

