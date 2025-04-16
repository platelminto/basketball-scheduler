# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands
- Run Django server: `python manage.py runserver`
- Create migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate` 
- Create superuser: `python manage.py createsuperuser`

## Testing
- Run Django tests: `python manage.py test scheduler`
- Run schedule tests: `python schedule_tests.py`
- Run all tests: `python manage.py test && python schedule_tests.py`
- Run specific validation test: `python -c "from tests import test_name; print(test_name(args))"`

## Code Style Guidelines
- **Python**: 4-space indentation, max line length ~88 chars
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Strings**: Double quotes for string literals
- **Docstrings**: Triple double quotes with parameter descriptions
- **Imports**: Standard libs → Django imports → Local imports
- **Types**: Use type hints (especially in utility functions)
- **Error handling**: Return (passed, errors) tuples from validation functions
- **Django**: Follow standard model conventions with descriptive Meta classes