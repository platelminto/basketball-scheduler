# League Schedule Generator

## Overview

This project is a sophisticated basketball league schedule generator designed to create balanced schedules for multi-level leagues. It uses advanced algorithms to generate schedules that satisfy various constraints and balance requirements.

## Features

- **Multi-Level Support**: Handles leagues with multiple divisions/levels (A, B, C)
- **Round-Robin Scheduling**: Ensures each team plays against every other team in their level
- **Referee Assignments**: Automatically assigns referees for each game
- **Balanced Scheduling**:
  - Controls how many times teams play in each time slot
  - Ensures fair referee assignments
  - Maintains balanced court usage across time slots
- **Constraint Satisfaction**:
  - Teams don't play and referee simultaneously
  - Referees are scheduled in adjacent time slots to their games
  - Configurable limits on how many times teams play in specific slots
- **Optimization**: Uses simulated annealing to improve schedule balance
- **Mirrored Scheduling**: Creates schedules where the second half mirrors the first half's matchups
- **Validation**: Comprehensive validation of generated schedules

## TODO

- [ ] Add support for different number of teams per level
- [ ] Add support for different slots per week

## Configuration

The schedule generator is highly configurable through the `config` dictionary: 
```python
config = {
    # League structure
    "levels": ["A", "B", "C"], # Names of the levels/divisions
    "teams_per_level": { # Number of teams in each level
        "A": 6,
        "B": 6,
        "C": 6,
    },
    # Schedule structure
    "courts_per_slot": {
        1: 2,
        2: 2,
        3: 2,
        4: 3,
    }, # Number of courts available in each slot (1-indexed)
    # Constraints for play balance
    "slot_limits": {
        1: 3, # Teams can play at most 3 games in slot 1
        2: 6, # Teams can play at most 6 games in slots 2 and 3
        3: 6,
        4: 4, # Teams can play at most 4 games in slot 4
    },
    # Constraints for referee balance
    "min_referee_count": 4, # Minimum times a team must referee in a season per level
    "max_referee_count": 6, # Maximum times a team can referee in a season per level
    # Optimization priorities
    "priority_slots": [1, 4], # Slots where balance is more important
    "priority_multiplier": 100, # Extra weight for priority slots in balance calculations
}
```


## Algorithm

The schedule generation process follows these steps:

1. **Round-Robin Generation**: Creates a round-robin pairing for each level
2. **First Half Scheduling**: Uses backtracking to assign time slots and referees for the first half
3. **Second Half Scheduling**: Mirrors the first half's pairings with new slot and referee assignments
4. **Schedule Balancing**: Uses simulated annealing to improve the balance of play and referee assignments
5. **Validation**: Ensures the final schedule meets all constraints

## Usage

To generate a schedule:

```python
from schedule import find_schedule
# Generate a new schedule
final_schedule, total_attempts = find_schedule(use_saved_schedule=False)

# Print the schedule
from utils import print_schedule
print_schedule(final_schedule)

# Save the schedule to a file
from utils import save_schedule_to_file
save_schedule_to_file(final_schedule, "my_schedule.json")
```


## Advanced Features

- **Parallel Processing**: Uses multiprocessing to try multiple schedule attempts in parallel
- **Statistics**: Provides detailed statistics about the generated schedules
- **Testing**: Includes comprehensive tests to validate schedule properties

## Integration with Django

This schedule generator is designed to be integrated with a Django web application:

- The `scheduler` app provides models for teams, levels, and saved schedules
- The web interface allows generating, viewing, and managing schedules
- Schedules can be saved and loaded from the database

## Requirements

- Python 3.8+
- Required packages:
  - Django (for web interface)
  - Other standard libraries (json, random, itertools, etc.)

## License

This project is available for use under the terms specified in the LICENSE file.