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

## API Endpoints
- Seasons: `/scheduler/api/seasons/`
- Season details: `/scheduler/api/seasons/{season_id}/`
- Activate season: `/scheduler/api/seasons/{season_id}/activate/`
- Validate schedule: `/scheduler/api/seasons/{season_id}/validate/`
- Generate schedule: `/scheduler/api/seasons/{season_id}/generate/`
- Update teams/levels: `/scheduler/api/seasons/{season_id}/teams/`
- Save/update schedule: `/scheduler/api/seasons/{season_id}/schedule/`
- Public schedule: `/scheduler/api/public/schedule/`
- Edit scores redirect: `/scheduler/edit-scores/`

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