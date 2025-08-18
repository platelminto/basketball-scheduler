"""
Scheduler services module.

This module provides organized service functions for business logic
separated from HTTP handling in views.
"""

# Game operations
from .game_operations import (
    normalize_game_data,
    resolve_game_objects,
    parse_game_fields,
)

# Season management
from .seasons import (
    get_seasons_data,
    activate_season_logic,
    update_season_organization,
)

# Schedule validation
from .validation import (
    run_all_validation_tests,
    validate_schedule_data,
)

# Schedule generation
from .generation import (
    generate_schedule_async,
    handle_generation_cancellation,
    validate_generation_constraints,
    format_generated_schedule,
)

# Schedule CRUD operations
from .schedules import (
    create_schedule,
    update_schedule,
    build_schedule_response_data,
    normalize_time_field,
)

# Schedule data retrieval
from .schedule_data import (
    get_schedule_data_for_season,
    get_public_schedule_data,
    get_teams_and_levels_data,
    format_games_by_week,
)

# Team and level management - using new team_management service

# Calendar export
from .calendar import (
    generate_team_calendar,
    handle_calendar_options,
)

__all__ = [
    # Game operations
    "normalize_game_data",
    "resolve_game_objects", 
    "parse_game_fields",
    
    # Season management
    "get_seasons_data",
    "activate_season_logic",
    
    # Schedule validation
    "run_all_validation_tests",
    "validate_schedule_data",
    
    # Schedule generation
    "generate_schedule_async",
    "handle_generation_cancellation",
    "validate_generation_constraints",
    "format_generated_schedule",
    
    # Schedule CRUD operations
    "create_schedule",
    "update_schedule", 
    "build_schedule_response_data",
    "normalize_time_field",
    
    # Schedule data retrieval
    "get_schedule_data_for_season",
    "get_public_schedule_data",
    "get_teams_and_levels_data",
    "format_games_by_week",
    
    # Team and level management
    
    # Calendar export
    "generate_team_calendar",
    "handle_calendar_options",
]