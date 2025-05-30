# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure
- Django backend with React frontend
- Single Page Application (SPA) for the scheduler interface
- Uses React Router for client-side routing
- Context API for state management

## Build Commands
- Run Django server: `python manage.py runserver`
- Create migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Create superuser: `python manage.py createsuperuser`
- Build frontend assets: `npm run build` (webpack in production mode)
- Watch frontend assets for development: `npm run dev` (webpack in development mode)

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
- Schedule edit routes: `/scheduler/app/schedule/:seasonId/edit`
- All React routes under `/scheduler/app/` are handled by the React Router

## API Endpoints
- Season data: `/scheduler/api/seasons/`
- Schedule data: `/scheduler/api/schedule/:seasonId/`
- Update schedule: `/scheduler/schedule/:seasonId/update/`

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