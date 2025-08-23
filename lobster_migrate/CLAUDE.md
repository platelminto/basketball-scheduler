# LeagueLobster Schedule Import

This folder contains scripts to import basketball schedules from LeagueLobster text exports into our Django models.

## What it does
- Parses LeagueLobster schedule exports (text format)
- Extracts teams, games, scores, referees, and off-weeks
- Imports into Django Season/Team/Game models with proper relationships
- Assigns courts dynamically (1 game = Court 3, 2 games = Courts 2+3, 3 games = Courts 1+2+3)
- Handles off-weeks by dynamically mapping week numbers (off-weeks push subsequent weeks forward)

## Process
1. **Parse standings** → extract teams by skill level (Top/High/Mid)
2. **Parse schedule** → extract games in format: Time → Level → [Referee] → Team1 → Score → Team2
3. **Dynamic week mapping** → adjust week numbers based on off-weeks encountered
4. **Court assignment** → assign courts based on concurrent games per time slot
5. **Import to Django** → create all models with proper foreign key relationships

## Pattern
- Try import → check for validation errors → fix parser → delete season → retry
- Week numbering must match system expectations (games 73-90 need weeks 11-12)
- Each team must have exactly 10 games for validation to pass

## Usage
```bash
uv run python lobster_migrate/2425/import_2425_02.py lobster_migrate/2425/2425_02.txt
```