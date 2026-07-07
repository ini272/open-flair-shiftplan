# Festival Shift Scripts

## Production Shifts
Use `create_production_shifts.py` to create the actual festival shifts from the YAML configuration:

```bash
python scripts/create_production_shifts.py --access-code YOUR_COORDINATOR_CODE
```

Or specify a custom YAML file:
```bash
python scripts/create_production_shifts.py --access-code YOUR_COORDINATOR_CODE --schedule path/to/custom_schedule.yaml
```

## Test Shifts
Use `create_test_shifts.py` to create random test shifts for development:

```bash
COORDINATOR_CODE=YOUR_COORDINATOR_CODE python scripts/create_test_shifts.py
```

## Demo Profiles
Use `seed_demo_profiles.py` to create deterministic demo users and a demo group with different availability patterns:

```bash
python scripts/seed_demo_profiles.py --api-url http://localhost:8000
```

This script assumes shifts already exist and uses the normal access-code login flow.

## Configuration
Edit `festival_schedule.yaml` to customize:
- Festival dates
- Locations (Weinzelt, Bierwagen, etc.)
- Daily schedules with specific times and capacities
- Shift descriptions
