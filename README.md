# CodeDuels ⚔️

A 1v1 coding duel platform where two players compete to solve the same programming problems. The faster and more accurate solver wins and earns rating points.

## Features
- **Placement Test** – New users take a placement test to determine their starting rating
- **Question Bank** – Browse and practice problems with search/filter by category and difficulty
- **Quick Match** – Get matched with a similarly-rated opponent automatically
- **Private 1v1** – Challenge a friend with an invite code (WebSocket-powered)
- **Live Progress** – See your opponent's progress in real-time
- **Elo Rating** – Rating system with correctness and speed bonuses
- **Leaderboard** – See top-ranked players and export to CSV
- **Problem Importer** – Import draft problems from the Codeforces API

## Stack
- Python / Django
- SQLite
- Django Channels + Daphne (WebSockets, in-memory channel layer)
- Bootstrap 5 (CDN)
- Plain JavaScript

## Setup
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_problems    # optional: load sample problems
python manage.py runserver
```

## Warning
The code judge uses `subprocess` and is **not sandboxed**. Only run on a trusted network.
