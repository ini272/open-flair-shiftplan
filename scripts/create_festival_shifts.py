import requests
import datetime

# Configuration
API_URL = "http://localhost:8000"
TOKEN = "3142f655-3724-422f-bc2c-c1c0e2de2b07"  # Replace with a valid admin token
FESTIVAL_START = datetime.datetime(2025, 8, 6)
FESTIVAL_END = datetime.datetime(2025, 8, 11)  # Day after festival ends
LOCATIONS = ["Weinzelt", "Bierwagen"]
SHIFT_TYPES = [
    {"name": "Morning", "start_hour": 8, "end_hour": 12},
    {"name": "Afternoon", "start_hour": 12, "end_hour": 16},
    {"name": "Evening", "start_hour": 16, "end_hour": 20},
    {"name": "Night", "start_hour": 20, "end_hour": 0}
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
            
            # Create shift
            shift_data = {
                "title": f"{location} - {shift_type['name']}",
                "description": f"Shift at {location} during {shift_type['name']} hours",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "capacity": 3  # Adjust as needed
            }
            
            response = session.post(f"{API_URL}/shifts/", json=shift_data)
            if response.status_code == 201:
                shifts_created += 1
                print(f"Created shift: {shift_data['title']} on {current_date.date()}")
            else:
                print(f"Failed to create shift: {response.text}")
    
    # Move to next day
    current_date += datetime.timedelta(days=1)

print(f"Created {shifts_created} shifts for the festival")