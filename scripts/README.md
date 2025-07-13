# Festival Shift Scripts

## Production Shifts
Use `create_production_shifts.py` to create the actual festival shifts from the YAML configuration:

```bash
python scripts/create_production_shifts.py
```

Or specify a custom YAML file:
```bash
python scripts/create_production_shifts.py path/to/custom_schedule.yaml
```

## Test Shifts
Use `create_test_shifts.py` to create random test shifts for development:

```bash
python scripts/create_test_shifts.py
```

## Configuration
Edit `festival_schedule.yaml` to customize:
- Festival dates
- Locations (Weinzelt, Bierwagen, etc.)
- Daily schedules with specific times and capacities
- Shift descriptions