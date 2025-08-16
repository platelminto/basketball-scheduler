# Plan: Refactor views.py into Services Directory

**Goal**: Split the massive 1120-line `views.py` into focused, maintainable modules using Django service layer pattern.

## 1. Create Services Directory Structure
- Create `scheduler/services/` directory
- Move existing `services.py` → `services/game_operations.py`
- Create `__init__.py` with service imports

## 2. Split Views into Service Modules
Create these focused service modules:

### `services/seasons.py`
- `get_seasons_data()` - Season listing logic
- `activate_season_logic()` - Season activation business rules
- Extract from: `get_seasons()`, `activate_season()`

### `services/validation.py`
- `validate_schedule_data()` - Schedule validation orchestration
- `run_all_validation_tests()` - Test runner logic
- Extract from: `validate_schedule()`

### `services/generation.py`
- `generate_schedule_async()` - Schedule generation with threading
- `handle_generation_cancellation()` - Cancellation logic
- `validate_generation_constraints()` - Generation validation
- Extract from: `auto_generate_schedule()`, `cancel_schedule_generation()`

### `services/schedules.py`
- `create_schedule()` - Schedule creation logic
- `update_schedule()` - Schedule update logic
- `build_schedule_response_data()` - Response formatting
- Extract from: `save_or_update_schedule()`

### `services/schedule_data.py`
- `get_schedule_data_for_season()` - Data retrieval logic
- `format_games_by_week()` - Data formatting
- `get_teams_and_levels_data()` - Related data retrieval
- Extract from: `_get_schedule_data()`, `schedule_data()`, `public_schedule_data()`

### `services/teams.py`
- `update_teams_and_levels()` - Team/level CRUD logic
- `handle_team_deletions()` - Safe deletion logic
- `process_level_updates()` - Level update logic
- Extract from: `update_teams_levels()`

### `services/calendar.py`
- `generate_team_calendar()` - iCal generation logic
- `format_calendar_events()` - Event formatting
- `handle_calendar_options()` - Query parameter processing
- Extract from: `team_calendar_export()`

## 3. Update Views to Use Services
- Keep views thin - only handle HTTP concerns
- Import and call service functions
- Maintain existing API contracts
- Preserve error handling patterns

## 4. Update Imports
- Update existing imports in views.py
- Update services/__init__.py to expose all services
- Ensure no circular imports

## Benefits
- **Maintainability**: Each service has single responsibility
- **Testability**: Business logic separated from HTTP handling
- **Reusability**: Services can be used across different views
- **Readability**: Much shorter, focused files
- **Scalability**: Easy to add new functionality to specific domains

This follows Django best practices and uses clean domain-based naming without the `_service` suffix.