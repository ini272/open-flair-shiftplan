import requests
import datetime

# Configuration
API_URL = "http://localhost:8000"
TOKEN = "58482b6b-3e15-4fb1-bb54-3bb19e82f048"  # Replace with a valid admin token
FESTIVAL_START = datetime.datetime(2025, 8, 6)
FESTIVAL_END = datetime.datetime(2025, 8, 11)  # Day after festival ends
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

# Login with token
session = requests.Session()
response = session.get(f"{API_URL}/auth/login/{TOKEN}")
if response.status_code != 200:
    print(f"Login failed: {response.text}")
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
