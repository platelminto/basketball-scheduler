# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure
- Django backend with React frontend
- Single Page Application (SPA) for the scheduler interface
- Uses React Router for client-side routing
- Context API for state management
- Uses `uv` - all `python` commands should use `uv run`.

## Build Commands
- Run Django server: `python manage.py runserver`
- Create migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Create superuser: `python manage.py createsuperuser`
- Build frontend assets: `npm run build` (webpack in production mode)
- Watch frontend assets for development: `npm run dev` (webpack in development mode)
- IMPORTANT: Don't try and run a lot of these commands yourself, I'm usually running them in the background already. Tell me to run them if you want.

## Testing
- Run Django tests: `python manage.py test scheduler`
- Run schedule tests: `python schedule_tests.py`
- Run all tests: `python manage.py test && python schedule_tests.py`
- Run specific validation test: `python -c "from tests import test_name; print(test_name(args))"`
- DO NOT start the server to test web features - user will handle testing themselves
- Make code changes, but let the user test the implementation with their own server instance
- If you want to test something, don't just create and run something on the spot - actually create a test we can use long-term, and run that. Tests usually go in `scheduler/tests`

## Frontend Architecture
- Main entry point: `/assets/js/schedule-app/index.js`
- Unified React SPA with React Router
- Component structure:
  - `/components/` - Reusable UI components
  - `/pages/` - Page-level components mapped to routes
  - `/contexts/` - React Context providers for state management
  - `/hooks/` - Custom React hooks
  - `/styles/` - CSS files

## URL Structure
- Django routes: `/scheduler/...`
- SPA base route: `/scheduler/app/`
- All React routes under `/scheduler/app/` are handled by the React Router

## Detailed Project Structure
- `/scheduler/`: Django app containing models, views, and templates
  - `/services/`: Business logic layer for schedule operations
  - `/auth_views.py`: Authentication endpoints and decorators
  - `/tests/`: Comprehensive Django test suite
- `/assets/js/schedule-app/`: React application
  - `/components/`: Reusable UI components
  - `/pages/`: Page-level components mapped to routes
  - `/contexts/`: React Context providers (AuthContext, ScheduleContext)
  - `/hooks/`: Custom React hooks
  - `/styles/`: CSS files
  - `/utils/`: Utility functions for data transformation and API calls
- `/schedule.py`: Core schedule generation algorithm
- `/lobster_migrate/`: Data migration tools for importing historical data

## API Endpoints

### Authentication Endpoints
- Login: `/scheduler/auth/login/`
- Logout: `/scheduler/auth/logout/`
- Authentication status: `/scheduler/auth/status/`
- CSRF token: `/scheduler/auth/csrf-token/`

### Season Management
- Seasons list: `/scheduler/api/seasons/`
- Season details: `/scheduler/api/seasons/{season_id}/`
- Activate season: `/scheduler/api/seasons/{season_id}/activate/`
- Delete season: `/scheduler/api/seasons/{season_id}/delete/`
- Season standings: `/scheduler/api/seasons/{season_id}/standings/`
- Generate schedule: `/scheduler/api/seasons/{season_id}/generate/`
- Cancel generation: `/scheduler/api/seasons/cancel-generation/`
- Generation progress: `/scheduler/api/seasons/generation-progress/`
- Save/update schedule: `/scheduler/api/seasons/{season_id}/schedule/`

### Team Management
- Teams list: `/scheduler/api/teams/`
- Team details: `/scheduler/api/teams/{team_id}/`
- Archive team: `/scheduler/api/teams/{team_id}/archive/`
- Team statistics: `/scheduler/api/teams/{team_id}/stats/`
- Team history: `/scheduler/api/teams/{team_id}/history/`
- Season available teams: `/scheduler/api/seasons/{season_id}/available-teams/`
- Assign teams to season: `/scheduler/api/seasons/{season_id}/assign-teams/`
- Update team levels: `/scheduler/api/seasons/{season_id}/team-levels/`
- Remove teams from season: `/scheduler/api/seasons/{season_id}/remove-teams/`

### Public & Export
- Public schedule: `/scheduler/api/public/schedule/`
- Team calendar export: `/scheduler/api/team-orgs/{team_org_id}/calendar.ics`

## Schedule Generation Algorithm

The schedule generation uses a **two-phase optimization approach** with linear programming:

### Phase 1: Matchup Blueprint Generation
- Uses **PuLP** (linear programming) to generate multiple unique round-robin matchup blueprints
- Ensures each team plays every other team in their level equally across the season
- Implements **mirrored scheduling** where second half mirrors first half matchups
- Creates multiple valid matchup combinations for Phase 2 to optimize
- Uses constraint satisfaction to find diverse blueprint options

### Phase 2: Slot & Referee Assignment Optimization
- Takes each matchup blueprint and optimizes time slot and referee assignments
- Uses **weighted penalty system** with sophisticated objective function:
  - **Slot balance**: Teams distributed fairly across time slots based on court availability
  - **First/last slot protection**: Higher penalties (500pt) for too many inconvenient times
  - **Referee balance**: Soft limits (±1 from target) with 1000pt penalties for violations
  - **Adjacent slot rule**: Referees must play in time slots adjacent to when they referee
- Evaluates all blueprints and selects the one with lowest imbalance score
- Supports **cancellation** and **early termination** during optimization

### Automatic Balancing System
The algorithm uses **weighted soft constraints** instead of hard limits:
- **Slot Distribution Balancing**: Target-based calculations with weighted penalties (15x higher for first/last slots)
- **Referee Balancing**: Soft hard limits with teams refereeing target ±1 games
- **First/Last Slot Protection**: Special constraints with 500pt penalties for too many inconvenient times
- **No Manual Configuration Required**: Algorithm automatically determines optimal balance

## Schedule Configuration

The schedule generator requires minimal configuration - just team names and court availability:

```python
# Define teams by level/division
team_names_by_level = {
    "A": ["TeamA1", "TeamA2", "TeamA3", "TeamA4", "TeamA5", "TeamA6"],
    "B": ["TeamB1", "TeamB2", "TeamB3", "TeamB4", "TeamB5", "TeamB6"], 
    "C": ["TeamC1", "TeamC2", "TeamC3", "TeamC4", "TeamC5", "TeamC6"],
}

# Define court availability per time slot per week
courts_per_slot = {
    1: [1, 1, 2, 2, 2, 2, 2, 2, 2, 2],  # Slot 1: courts available each week
    2: [3, 3, 2, 2, 2, 2, 2, 2, 2, 2],  # Slot 2: courts available each week
    3: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # Slot 3: courts available each week
    4: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],  # Slot 4: courts available each week
}

# Generate schedule with optimization
schedule = generate_schedule(
    courts_per_slot=courts_per_slot,
    team_names_by_level=team_names_by_level,
    time_limit=60.0,           # Total optimization time in seconds
    num_blueprints_to_generate=6,  # Number of matchup blueprints to try
    gapRel=0.25               # Solver optimality gap tolerance
)
```


## Code Style Guidelines
- **Python**: 4-space indentation, max line length ~88 chars
- **JavaScript**: 2-space indentation, use ES6+ features
- **React**: Function components with hooks (no class components)
- **Naming**:
  - Python: snake_case for functions/variables, PascalCase for classes
  - JavaScript: camelCase for variables/functions, PascalCase for components
- **Strings**: Double quotes for string literals
- **Docstrings**: Triple double quotes with parameter descriptions
- **Imports**: Standard libs → Django/React imports → Local imports
- **Types**: Use type hints in Python (especially in utility functions)
- **Error handling**: Return (passed, errors) tuples from validation functions
- **Django**: Follow standard model conventions with descriptive Meta classes

## Design System & Styling
**CRITICAL**: This project uses a unified design system. DO NOT create component-specific CSS files or duplicate styles.

### CSS Architecture
- **Single source of truth**: All styles in `/assets/js/schedule-app/styles/main.css`
- **CSS Custom Properties**: Use CSS variables for consistency (`--primary`, `--success`, etc.)
- **No component-specific CSS files**: Everything is unified in main.css
- **No duplicate button systems**: Use the single `.btn` system only

### UI Components - Always Use These Classes
- **Containers**: `.page-container`, `.app-container`, `.content-container`
- **Buttons**: `.btn` with variants (`.btn-primary`, `.btn-success`, `.btn-danger`, etc.)
  - Sizes: `.btn-sm`, `.btn-lg`, `.btn-icon`
  - Outlines: `.btn-outline-primary`, `.btn-outline-secondary`
- **Cards**: `.card`, `.card-header`, `.card-content`, `.card-title`
- **Forms**: `.form-section`, `.form-control`, `.form-select`, `.form-label`
- **Alerts**: `.alert` with variants (`.alert-success`, `.alert-danger`, `.alert-warning`, `.alert-info`)
- **Badges**: `.badge` with variants (`.badge-success`, `.badge-warning`, etc.)
- **Tables**: `.table` (fully styled system included)
- **Loading**: `.loading-container`, `.spinner`

### Color Palette (CSS Variables)
```css
--primary: #3b82f6 (blue)
--success: #10b981 (green) 
--danger: #ef4444 (red)
--warning: #f59e0b (orange)
--secondary: #6b7280 (gray)
--text-primary: #1f2937
--text-secondary: #6b7280
--bg-primary: #ffffff
--border-primary: #e5e7eb
```

### Styling Rules
1. **NEVER** import or create component-specific CSS files
2. **ALWAYS** use the unified classes from main.css
3. **USE** CSS custom properties for colors (`var(--primary)`)
4. **PREFER** utility classes over inline styles when possible
5. **FOR** complex layouts, use inline styles with CSS variables
6. **MAINTAIN** consistency - if a style exists, use it; don't recreate it

### Examples
```jsx
// ✅ GOOD - Uses unified system
<div className="page-container">
  <button className="btn btn-primary">Save</button>
  <div className="alert alert-success">Success!</div>
</div>

// ❌ BAD - Creates component-specific styles
import './MyComponent.css';
<button className="my-custom-button">Save</button>

// ✅ GOOD - Inline styles with CSS variables
<div style={{ color: 'var(--text-secondary)', padding: 'var(--space-lg)' }}>

// ❌ BAD - Hardcoded values
<div style={{ color: '#6b7280', padding: '1rem' }}>
```