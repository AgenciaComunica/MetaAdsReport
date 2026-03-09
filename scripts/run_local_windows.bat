@echo off
cd /d %~dp0\..

if not exist .venv (
    py -3.12 -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
)

python project\manage.py migrate
python project\manage.py runserver
