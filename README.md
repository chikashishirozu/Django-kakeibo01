# Django Kakeibo (Household Budget App)

A multi-user household budget app built with Django.
Each user sees only their own income and expenses.

## Features

- Dashboard: this month's income / expense / balance, yearly savings and goal progress
- Add, edit and delete income and expense entries
- Monthly view with per-category totals and pagination
- Yearly bar chart (income vs. expense for every month)
- Yearly savings goals (per user)
- Login, logout and sign-up (sign-up can be switched off)

## Requirements

- Python 3.10 or later (3.13 recommended)
- Django 5.2 LTS (installed by `requirements.txt`)

## Quick start (local development)

Run these commands in the project root (the directory that contains `manage.py`).

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # default values are fine for local use

python manage.py migrate            # create db.sqlite3
python manage.py setup_categories   # load the initial categories (required on an empty DB)
python manage.py createsuperuser    # create the first user

python manage.py runserver
```

Open <http://127.0.0.1:8000/budget/> and log in.

| URL | Page |
| --- | --- |
| `/budget/` | Dashboard |
| `/budget/goals/` | Yearly goals |
| `/accounts/signup/` | Sign up (only when `ALLOW_SIGNUP=True`) |
| `/admin/` | Django admin |

## Management commands

```bash
python manage.py setup_categories --help
python manage.py setup_categories                              # add the default categories
python manage.py setup_categories --user alice --goal 300000   # also create alice's goal for this year
python manage.py changepassword alice                          # reset a forgotten password
```

> **Warning: `setup_categories --reset` deletes every category, and because of
> `on_delete=CASCADE` it also deletes every budget entry that uses them.**
> Back up `db.sqlite3` first (`cp db.sqlite3 db.sqlite3.bak`).

## Tests

```bash
python manage.py test budget.tests
```

Run this again after upgrading Python or any package.

## Deployment notes

The development server (`runserver`) is not meant for production.
Before exposing the app to the internet:

1. Set the production values in `.env` (see the commented block in `.env.example`):
   a new `DJANGO_SECRET_KEY`, `DEBUG=False` and your real `ALLOWED_HOSTS`.
2. Serving over HTTPS? Set `USE_HTTPS=True` (and `BEHIND_PROXY=True` behind a reverse proxy).
   Start with a short `SECURE_HSTS_SECONDS` and raise it gradually.
3. Collect static files (served by WhiteNoise):
   ```bash
   python manage.py collectstatic --noinput
   ```
4. Run `python manage.py check --deploy` and review the warnings.
5. Close sign-up with `ALLOW_SIGNUP=False` once everyone has registered.

Never commit `.env` or `db.sqlite3`.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `400 Bad Request` on every page | The host name is not in `ALLOWED_HOSTS`. Add `127.0.0.1,localhost` to `.env` and restart. |
| `AttributeError: 'super' object has no attribute 'dicts'` | Django is too old for your Python (for example Django 4.2 with Python 3.14+). Run `pip install -r requirements.txt`, then **restart** `runserver`. |
| `'budget' is not a registered namespace` | `budget/urls.py` is empty or outdated. Make sure all project files are up to date. |
| `Unknown command: 'setup_categories'` | Run the command from the directory that contains `manage.py`, and check that `'budget'` is in `INSTALLED_APPS`. |
| The category list is empty on the entry form | Run `python manage.py setup_categories`. |
| Forgot the password | `python manage.py changepassword <username>` |
| Still the old behaviour after `pip install` | The running server keeps the old libraries in memory. Stop it with Ctrl+C and start it again. |

## License

No license is specified. All rights are reserved by the author.
