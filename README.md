# Family Calendar Auto-Color Fixer

Automatically fixes event colors in a shared Google Family calendar using keyword rules.

## Category Mapping

- Grape -> Studies
- Green -> Pre-school related events and reminders
- Peach -> Travelling
- Lavender -> Visits

`config.example.yaml` maps these categories to Google event `color_id` values. Adjust IDs after checking your account's palette.

## 1) Prerequisites

- Python 3.10+
- Google Cloud project with Calendar API enabled
- OAuth client credentials file (`credentials.json`, desktop app type)

### OAuth scopes (important)

This app uses **`https://www.googleapis.com/auth/calendar`** (full Calendar access) so it can **list/patch events** and call **`colors.get()`** for `--print-colors`. Narrow scopes like `calendar.events` alone are **not** enough for the Colors API and return **403 insufficientPermissions**.

In **Google Cloud Console** → **APIs & Services** → **OAuth consent screen** → **Edit app** → **Scopes** → **Add or remove scopes**, include **Google Calendar API** → *See, edit, share, and permanently delete all the calendars you can access using Google Calendar* (`.../auth/calendar`).

After changing scopes, **delete** `.secrets/token.json` (or your `google.token_file`) and run again so the browser asks for the updated permissions.

## 2) Setup

1. Copy config:
   - `cp config.example.yaml config.yaml`
2. Install dependencies:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Put your OAuth file at project root:
   - `credentials.json`
4. Edit `config.yaml`:
   - set `google.calendar_id` to your family calendar ID
   - tune keywords and precedence under `classification`
   - set `run.dry_run` to `true` initially

## 3) Find Correct Color IDs

Print available Google event colors:

`python3 src/main.py --config config.yaml --print-colors`

Then update each category `color_id` in `config.yaml`.

## 4) Run Manually

- Dry run:
  - `python3 src/main.py --config config.yaml --dry-run`
- Force write mode:
  - `python3 src/main.py --config config.yaml --write`

On first run, browser OAuth consent opens and token is stored at `google.token_file` (default `.secrets/token.json`).

## 5) Cron Job

Example (every 15 minutes):

`*/15 * * * * /usr/bin/env bash -lc 'cd /home/maxandersson/family-calendar-color-fixer && /usr/bin/python3 src/main.py --config config.yaml >> /home/maxandersson/family-calendar-color-fixer/cron.log 2>&1'`

Install with:

1. `crontab -e`
2. Paste the line above
3. Save and exit

The script includes a lock file (`run.lock_file`) so overlapping cron runs are skipped safely.

## 6) Run Tests

Run the unit tests for classification logic:

`python3 -m unittest discover -s tests -v`

## Rule Behavior

- Matches against event title, description, and location
- Case-insensitive keyword matching
- Optional `exclude_keywords` per category
- Uses deterministic priority order (`classification.priority`)
- Updates only events in configured date window (`window_days`)
- Skips cancelled events

## Troubleshooting

- `FileNotFoundError: credentials.json`:
  - Place OAuth desktop client file at configured path.
- No events are updated:
  - Check category keywords and `color_id` values.
  - Run with `--dry-run --verbose` to inspect matches.
- Permission errors in cron:
  - Use full paths and verify the same Python environment is available to cron.
