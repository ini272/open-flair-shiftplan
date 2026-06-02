#!/usr/bin/env python3
"""
Create production festival shifts from YAML configuration.
This script reads the festival schedule from a YAML file and creates shifts via the API.
"""

import requests
import yaml
import sys
import os
import argparse
from datetime import datetime, timedelta

# Configuration
API_URL = "http://localhost:8000"

def load_schedule(yaml_file: str) -> dict:
    """Load the festival schedule from YAML file."""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: Could not find schedule file: {yaml_file}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)

def clear_existing_shifts(session: requests.Session, api_url: str):
    """Clear all existing shifts."""
    print("🗑️  Clearing all existing shifts...")
    
    # First clear all assignments
    response = session.delete(f"{api_url}/shifts/all-assignments")
    if response.status_code == 200:
        print("   ✅ Cleared all shift assignments")
    else:
        print(f"   ⚠️  Warning: Could not clear assignments: {response.text}")
    
    # Get all shifts
    response = session.get(f"{api_url}/shifts/")
    if response.status_code != 200:
        print(f"   ❌ Failed to get existing shifts: {response.text}")
        return
    
    shifts = response.json()
    deleted_count = 0
    
    # Delete each shift
    for shift in shifts:
        delete_response = session.delete(f"{api_url}/shifts/{shift['id']}")
        if delete_response.status_code == 204:
            deleted_count += 1
        else:
            print(f"   ⚠️  Failed to delete shift {shift['title']}: {delete_response.text}")
    
    print(f"   ✅ Deleted {deleted_count} shifts")
    print()

def create_shifts_from_schedule(session: requests.Session, schedule_data: dict, api_url: str):
    """Create shifts based on the schedule configuration."""
    
    festival_info = schedule_data['festival']
    locations = [loc['name'] for loc in schedule_data['locations']]
    schedule = schedule_data['schedule']
    
    print(f"Creating shifts for {festival_info['name']}")
    print(f"Festival dates: {festival_info['start_date']} to {festival_info['end_date']}")
    print(f"Locations: {', '.join(locations)}")
    print()
    
    total_shifts_created = 0
    
    # Process each day in the schedule
    for date_str, day_config in schedule.items():
        print(f"Processing {date_str}...")
        
        # Parse the date
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"Warning: Invalid date format '{date_str}', skipping...")
            continue
        
        # Create shifts for each time slot on this day
        for shift_config in day_config['shifts']:
            # Parse times
            start_time_str = shift_config['start_time']
            end_time_str = shift_config['end_time']
            
            start_hour, start_minute = map(int, start_time_str.split(':'))
            end_hour, end_minute = map(int, end_time_str.split(':'))
            
            # If shift starts at 00:xx, it's actually the next day (late night shift)
            if start_hour == 0:
                # This is a late night shift - move it to the next day
                start_datetime = (date_obj + timedelta(days=1)).replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                end_datetime = (date_obj + timedelta(days=1)).replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
                print(f"  📅 Late night shift: {start_time_str}-{end_time_str} moved to {start_datetime.strftime('%Y-%m-%d')}")
            else:
                start_datetime = date_obj.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                
                # If end time is earlier than start time, it's next day
                if end_hour < start_hour or (end_hour == start_hour and end_minute <= start_minute):
                    end_datetime = (date_obj + timedelta(days=1)).replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
                else:
                    end_datetime = date_obj.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            
            # Create shifts for each location
            for location in locations:
                # Just use location as title
                title = location
                full_description = f"{location} shift from {start_time_str} to {end_time_str}"
                
                # Create shift data
                shift_data = {
                    "title": title,
                    "description": full_description,
                    "start_time": start_datetime.isoformat(),
                    "end_time": end_datetime.isoformat(),
                    "capacity": shift_config['capacity']
                }
                
                # Create the shift via API
                response = session.post(f"{api_url}/shifts/", json=shift_data)
                
                if response.status_code == 201:
                    total_shifts_created += 1
                    print(f"  ✅ Created: {title} (Capacity: {shift_config['capacity']})")
                elif response.status_code == 400 and "already exists" in response.text.lower():
                    print(f"  ⚠️  Already exists: {title}")
                else:
                    print(f"  ❌ Failed to create: {title}")
                    print(f"     Error: {response.status_code} - {response.text}")
        
        print()
    
    return total_shifts_created

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create festival shifts from YAML configuration via API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_production_shifts.py --access-code zelt-plan-regen-48
  python create_production_shifts.py --access-code zelt-plan-regen-48 --clear-existing
  python create_production_shifts.py --access-code zelt-plan-regen-48 --schedule custom_schedule.yaml
  python create_production_shifts.py --access-code zelt-plan-regen-48 --api-url http://localhost:8001
        """
    )
    
    parser.add_argument(
        '--access-code', '-a',
        default=os.getenv("COORDINATOR_CODE") or os.getenv("OPEN_FLAIR_COORDINATOR_CODE"),
        help='Coordinator access code for API access (or set COORDINATOR_CODE)'
    )
    
    parser.add_argument(
        '--schedule', '-s',
        help='Path to YAML schedule file (default: festival_schedule.yaml in script directory)'
    )
    
    parser.add_argument(
        '--api-url', '-u',
        default=API_URL,
        help=f'API base URL (default: {API_URL})'
    )
    
    parser.add_argument(
        '--clear-existing', '-c',
        action='store_true',
        help='Clear all existing shifts before creating new ones'
    )
    
    args = parser.parse_args()
    if not args.access_code:
        parser.error("--access-code is required unless COORDINATOR_CODE is set")
    return args

def main():
    """Main function to create festival shifts."""
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Determine the path to the YAML file
    if args.schedule:
        yaml_file = args.schedule
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_file = os.path.join(script_dir, "festival_schedule.yaml")
    
    print(f"Loading schedule from: {yaml_file}")
    print(f"API URL: {args.api_url}")
    print()
    
    # Load the schedule
    schedule_data = load_schedule(yaml_file)
    
    # Login with coordinator access code
    session = requests.Session()
    print(f"Logging in to {args.api_url}...")
    response = session.post(
        f"{args.api_url}/auth/login",
        json={"access_code": args.access_code},
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        print("Make sure:")
        print(f"1. The FastAPI server is running on {args.api_url}")
        print("2. The coordinator access code is valid")
        sys.exit(1)

    login_data = response.json()
    if login_data.get("role") != "coordinator":
        print("❌ Login succeeded, but the access code is not a coordinator code")
        sys.exit(1)
    
    print("✅ Logged in successfully")
    print()
    
    try:
        # Clear existing shifts if requested
        if args.clear_existing:
            clear_existing_shifts(session, args.api_url)
        
        # Create shifts
        total_created = create_shifts_from_schedule(session, schedule_data, args.api_url)
        
        # Get summary from API
        shifts_response = session.get(f"{args.api_url}/shifts/")
        if shifts_response.status_code == 200:
            all_shifts = shifts_response.json()
            active_shifts = [s for s in all_shifts if s.get('is_active', True)]
            
            print(f"📊 Summary:")
            print(f"   Shifts created this run: {total_created}")
            print(f"   Total active shifts in database: {len(active_shifts)}")
        else:
            print(f"📊 Summary:")
            print(f"   Shifts created this run: {total_created}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
