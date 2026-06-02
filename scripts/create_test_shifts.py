import requests
import datetime
import os

# Configuration
API_URL = "http://localhost:8000"
ACCESS_CODE = os.getenv("COORDINATOR_CODE") or os.getenv("OPEN_FLAIR_COORDINATOR_CODE")
FESTIVAL_START = datetime.datetime(2026, 8, 5)
FESTIVAL_END = datetime.datetime(2026, 8, 10)  # Day after festival ends
LOCATIONS = ["Weinzelt", "Bierwagen"]
SHIFT_TYPES = [
    {"start_hour": 8, "end_hour": 10},
    {"start_hour": 10, "end_hour": 12},
    {"start_hour": 12, "end_hour": 14},
    {"start_hour": 14, "end_hour": 16},
    {"start_hour": 16, "end_hour": 18},
    {"start_hour": 18, "end_hour": 20},
    {"start_hour": 20, "end_hour": 22},
    {"start_hour": 22, "end_hour": 0}
]

# Login with coordinator access code
if not ACCESS_CODE:
    print("Set COORDINATOR_CODE to a valid coordinator access code before running this script.")
    exit(1)

session = requests.Session()
response = session.post(f"{API_URL}/auth/login", json={"access_code": ACCESS_CODE})
if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)

if response.json().get("role") != "coordinator":
    print("Login succeeded, but the access code is not a coordinator code")
    exit(1)

print("Logged in successfully")

# Create shifts for each day, location, and shift type
current_date = FESTIVAL_START
shifts_created = 0

while current_date < FESTIVAL_END:
    for location in LOCATIONS:
        for shift_type in SHIFT_TYPES:
            # Calculate shift times
            start_time = current_date.replace(hour=shift_type["start_hour"], minute=0)
            
            # Handle midnight case
            if shift_type["end_hour"] == 0:
                end_time = (current_date + datetime.timedelta(days=1)).replace(hour=0, minute=0)
            else:
                end_time = current_date.replace(hour=shift_type["end_hour"], minute=0)
            
            # Create shift with simplified title
            shift_data = {
                "title": location,
                "description": f"Shift at {location} from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "capacity": 3  # Adjust as needed
            }
            
            response = session.post(f"{API_URL}/shifts/", json=shift_data)
            if response.status_code == 201:
                shifts_created += 1
                print(f"Created shift: {shift_data['title']} on {current_date.date()} from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}")
            else:
                print(f"Failed to create shift: {response.text}")
    
    # Move to next day
    current_date += datetime.timedelta(days=1)

print(f"Created {shifts_created} shifts for the festival")
