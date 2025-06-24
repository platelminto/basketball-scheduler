# USBF League Schedule Generator

## Overview

This project is a basketball league schedule generator designed to create balanced schedules for multi-level leagues. It uses advanced algorithms to generate schedules that satisfy various constraints and balance requirements. The application has evolved into a full-featured web application with a React frontend and Django backend.

## Key Features

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
- **Modern Web Interface**: React-based Single Page Application for schedule management
- **Season Management**: Create and manage multiple seasons with different team rosters
- **Score Tracking**: Record and view game scores throughout the season

## Architecture

### Backend

- **Django**: Provides the web framework, models, views, and API endpoints
- **Python Schedule Generator**: Core algorithm for creating balanced schedules
- **RESTful API**: JSON endpoints for communication with the frontend

### Frontend

- **React**: Single Page Application for responsive UI
- **React Router**: Client-side routing for seamless navigation
- **Context API**: Global state management with reducers
- **Webpack**: Asset bundling and optimization

## Project Structure

- `/scheduler/`: Django app containing models, views, and templates
- `/assets/js/schedule-app/`: React application
  - `/components/`: Reusable UI components
  - `/pages/`: Page-level components mapped to routes
  - `/contexts/`: React Context providers
  - `/hooks/`: Custom React hooks
  - `/styles/`: CSS files
- `/schedule.py`: Core schedule generation algorithm

## Schedule Configuration

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

## Schedule Generation Algorithm

The schedule generation process follows these steps:

1. **Round-Robin Generation**: Creates a round-robin pairing for each level
2. **First Half Scheduling**: Uses backtracking to assign time slots and referees for the first half
3. **Second Half Scheduling**: Mirrors the first half's pairings with new slot and referee assignments
4. **Schedule Balancing**: Uses simulated annealing to improve the balance of play and referee assignments
5. **Validation**: Ensures the final schedule meets all constraints

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/platelminto/usbf-schedule.git
   cd usbf-schedule
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   # Option 1: Using traditional venv
   python -m venv .venv
   source .venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   npm install

   
   # Option 2: Using uv (recommended)
   uv sync
   npm install
   ```

3. Set up the database:
   ```bash
   python manage.py migrate
   ```

4. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

5. Build frontend assets:
   ```bash
   npm run build
   ```

## Development Workflow

1. Run the Django development server:
   ```bash
   python manage.py runserver
   ```

2. Watch frontend assets for development:
   ```bash
   npm run dev
   ```

## Usage

### Web Interface

1. Access the application at `http://localhost:8000/scheduler/app/`
2. Create a new season and set up teams
3. Generate a schedule or manually create games
4. Edit the schedule as needed
5. Record scores as games are played

### Programmatic Usage

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

## API Endpoints

- Season data: `/scheduler/api/seasons/`
- Schedule data: `/scheduler/api/schedule/:seasonId/`
- Update schedule: `/scheduler/schedule/:seasonId/update/`

## Testing

- Run Django tests: `python manage.py test scheduler`
- Run schedule tests: `python schedule_tests.py`
- Run all tests: `python manage.py test && python schedule_tests.py`

## Advanced Features

- **Parallel Processing**: Uses multiprocessing to try multiple schedule attempts in parallel
- **Statistics**: Provides detailed statistics about the generated schedules
- **Testing**: Includes comprehensive tests to validate schedule properties

## Requirements

- Python 3.8+
- Node.js 16+
- Django 4.x
- React 18.x
- Additional packages as listed in requirements.txt and package.json
