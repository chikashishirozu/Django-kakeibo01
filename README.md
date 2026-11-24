# Django-kakeibo01
I built a home budgeting app with Django.

# Virtual environment setup
```
phthon3.13 -m venv venv

source venv/bin/activate

pip install -r requirements.txt   # whitenoise が入っています

```
# Create staticfiles
```
python manage.py collectstatic --noinput

```
# Create a directory in the budget app
```
cd budget

mkdir -p management/commands

```
# Create the necessary __init__.py file (IMPORTANT!)
```
touch management/__init__.py

touch management/commands/__init__.py
```

# Create the .env file
```
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"

```
add new secret key

# Create db.sqlite3 file
```
cd household_budget

source venv/bin/activate

python manage.py migrate

python manage.py createsuperuser           # ユーザー名・パスワードを対話で入力

python manage.py setup_categories          # カテゴリの初期登録（空DBでは必須）
```
# (Use the same code from the previous time)

Industry Tip: Why do we need __init__.py?
To make it recognized as a Python "package". Django scans the management/commands/ directory and registers the .py files in it as commands. Without __init__.py, it will be treated as "just a directory" and will not be recognized.

# Run in the project root (where manage.py is located)
```
python manage.py setup_categories
```
More useful usage

Django home accounting app complete guide
Documents ∙ Version 2

Industry common: Custom command usage
In actual development sites, custom commands are used for the following purposes:

1. Database initialization
bash
```
python manage.py setup_initial_data

python manage.py import_legacy_data

python manage.py changepassword user

python manage.py createsuperuser           # ユーザー名・パスワードを対話で入力

python manage.py setup_categories          # カテゴリの初期登録（空DBでは必須）

```

2. Periodic tasks (via cron)

bash

# Run daily
```

python manage.py daily_report

python manage.py cleanup_old_data
```

3. Maintenance tasks

bash
```
python manage.py fix_data_inconsistency

python manage.py recalculate_totals
```
# Launch in development environment
```
python manage.py runserver 127.0.0.1:7003
```

Runtime troubleshooting

Common error 1: No module named 'budget.models'

Cause: Missing __init__.py file Solution: Place an empty __init__.py in each directory

Common error 2: Unknown command: 'setup_categories'

Cause: Django doesn't recognize the command Solution:

Check file placement
Check if 'budget' is registered in INSTALLED_APPS

Common error 3: apps aren't loaded yet
Cause: Django environment not initialized properly Solution: Run via python manage.py

Pro Tips 💡
Industry common sense: Always implement the --help option for custom commands. This will prevent your future self or colleagues from wondering, "What does this command do?"

Also, in a production environment, it is best practice to add the --dry-run option (which does not actually run the command, but only displays what it does). Countless developers have cried over deleting large amounts of data...😅

# Run App
$ source venv/bin/activate

(venv)$ python manage.py runserver 127.0.0.1:7007

Open brawser http://127.0.0.1:7007/budget/
