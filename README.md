# CodeDuels ⚔️

## Running this copy

### AI chatbot and AI Interview

Add `GROQ_API_KEY=your-groq-key` to `.env`, then restart Django. The chatbot and
interview features share this key and default to `openai/gpt-oss-20b`, which is
available on the [Groq Free Plan](https://console.groq.com/docs/rate-limits).
`GROQ_MODEL` can override the default with another model supporting JSON Object Mode.

Run `python manage.py migrate` before opening **AI Interview** (`/ai/`). The floating
**Ask AI** button appears throughout the application; sign in to send questions.
Choose AI/ML, Software Development, or Web Development. Each interview has three
core questions and one Grok-generated follow-up per question (six answers total).
Completed reports include per-answer feedback, strengths, weaknesses, and improvements.
The overall score is the mean of the six answer scores, rounded to one decimal.
XP equals that score × 10 (0–100 XP), credited once per completed session.
Recent sessions and reports are accessible only to their owner from `/ai/`.

Use HTTPS or localhost for camera/microphone access, preferably Chrome or Edge for
browser speech recognition. Camera video is only a live preview and is never recorded
or uploaded. **Record answer** captures only microphone tracks in memory (up to three
minutes per answer). **Stop & review** allows local audio playback and transcript
correction; audio is discarded on submission or exit. Browser speech recognition may
process audio through the browser vendor's service. Only reviewed text is sent to Grok;
transcripts and reports are stored in the application's database. Typing remains available
when permissions are denied or speech recognition is unsupported. Save & exit preserves
submitted answers; submit the current answer before leaving to retain it.

Provider failures retain the current answer for retry. Rate limiting uses Django's cache
(process-local by default); use a shared cache if deploying multiple workers.
Run `python manage.py test interviews.test_ai` for mocked provider and interview tests.

C++ submissions automatically detect `g++` on PATH or in the standard MSYS2
UCRT64/MinGW64 installation folders. The judge supplies the compiler directory
to both compilation and execution so runtime DLLs are found. Restart Django
after updating the judge. No Windows PATH changes are needed for standard MSYS2.

For voice interviews, open `/interview/`, choose a topic, use Dictate answer,
then Stop and review each transcript. Select consent and click Finish to send
all three answers to Groq for a 0–10 rating, feedback and improvement suggestions.
Use `http://localhost:8000/interview/` on the host for microphone access. LAN HTTP
may require typed transcripts. HTTP 401 from Groq means the configured key is
rejected; replace `GROQ_API_KEY` in `.env` and restart the server.

This project copy is at `C:\Users\Dell\Downloads\code-duals-new\code-duals-new`.
Its database is separate from any Desktop project copy. Start it with:

```powershell
cd C:\Users\Dell\Downloads\code-duals-new\code-duals-new
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_problems
python manage.py seed_interviews
python manage.py run_lan
```

Questions: `/problems/`. Coding interview tracks: `/interviews/`.
Voice interviews (DSA, AI/ML, web development): `/interview/`, also linked from
the coding interview page. Put a valid `GROQ_API_KEY` in the local `.env`, then
restart Django. Invalid credentials cannot produce AI ratings. Use localhost or
HTTPS for browser microphone access; LAN HTTP supports typed transcripts.

A 1v1 coding duel platform where two players compete to solve the same programming problems. The faster and more accurate solver wins and earns rating points.

## Features
- **Placement Test** – New users take a placement test to determine their starting rating
- **Question Bank** – Browse and practice problems with search/filter by category and difficulty
- **Quick Match** – Get matched with a similarly-rated opponent automatically
- **Private 1v1** – Challenge a friend with an invite code (WebSocket-powered)
- **Live Progress** – See your opponent's progress in real-time
- **Elo Rating** – Rating system with correctness and speed bonuses
- **Leaderboard** – See top-ranked players and export to CSV
- **Problem Importer** – Import local JSON problem bundles

## Stack
- Python / Django
- SQLite
- Django Channels + Daphne (WebSockets, in-memory channel layer)
- Bootstrap 5 (CDN)
- Plain JavaScript

## Setup
Accounts use username/password registration and login. No OAuth credentials are required.

Open PowerShell in the project folder and create an isolated environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_problems    # optional: load sample problems
python manage.py runserver
```

## Warning
The code judge uses `subprocess` and is **not sandboxed**. Only run on a trusted network.


## Arena additions
Quick matchmaking, private invite rooms with ready toggles, participant-only WebSocket notifications, polling fallback, results and leaderboard CSV are implemented.

Run `python manage.py test duels` for the two-session integration tests.
Run `python manage.py import_problems --limit 100` to import metadata. Add statements and test cases in Admin before publishing drafts.

## Codeforces Questions

Import the built-in curated set of Codeforces problems with **auto-generated test cases** (30 per problem — 3 visible + 27 hidden):

```bash
python manage.py import_codeforces
```

Options:

| Flag | Default | Meaning |
|---|---|---|
| `--sample N` | 3 | Visible sample test cases per problem |
| `--hidden N` | 27 | Hidden test cases per problem |

This seeds ~25 hand-curated Codeforces-style problems (Easy → Hard) covering
standard I/O topics such as number theory, DP, graphs, and strings. Problems
are published immediately and available to players.

To instead sync **metadata-only drafts** from the live Codeforces API (no test cases; requires internet):

```bash
python manage.py import_codeforces --catalogue
python manage.py import_codeforces --catalogue --watch --interval 3600
python manage.py import_codeforces --catalogue --tags "dp;greedy" --limit 100
```

Catalogue drafts appear in the question bank only after adding a statement and
test cases via Admin or `import_problem_bundle`.

## Automatic question updates

In a second terminal with the same Python environment, run:

```powershell
python manage.py import_problems --source leetcode --watch
```

This syncs LeetCode metadata immediately, then hourly while running. Use
`--interval 600` for ten-minute updates.
The question bank refreshes its list every minute. Existing draft metadata is
updated by source URL; published problems and local tests are preserved.
Provider errors retain saved questions and are retried on the next cycle.
A one-time run exits with an error if a source fails, even if the other succeeds.

LeetCode uses an undocumented catalogue
endpoint and may block access (HTTP 403), so its sync is best effort. Premium
questions are skipped. Metadata-only imports remain hidden from the question bank. These
catalogues do not include hidden tests: statements and tests must be added before
publishing a problem for local judging and duels.

## Play over the same Wi-Fi

Only the host laptop needs Python, this project, its database and the C++ compiler.
Other players only need a browser. On the host:

```powershell
python manage.py migrate
python manage.py seed_problems
python manage.py run_lan
```

The command listens on all interfaces and prints candidate local addresses.
Run `ipconfig` and find the Wi-Fi adapter's IPv4 address if several are shown.
Everyone, including the host, should open the same address, such as
`http://192.168.1.5:8000/`. Do not use localhost on player computers: that refers
to their own computer. Keep the host running, awake and connected to Wi-Fi.
Allow Python through Windows Firewall for Private networks when prompted.
Guest networks or access-point client isolation can prevent devices connecting.
Do not configure router port forwarding. Start one server process because queues
and WebSocket channels are in memory. Invite links and WebSockets use the current
browser hostname; copying invites also works over LAN HTTP.

Register/login normally, finish placement, create a private duel and share its
invite link. Two different accounts are required. Internet is needed for question
imports, but saved questions are stored on the host. Players sign in with their
username and password.

## Import local problems

Import a JSON bundle containing a statement, test cases and reference solution:

```powershell
python manage.py import_problem_bundle path/to/problem.json
```
Bundle format (the test suite must include hidden tests):

```json
{
  "title": "Your problem title",
  "source_url": "https://example.com/your-problem",
  "statement": "Full problem statement, input format, output format and constraints.",
  "difficulty": "Easy",
  "time_limit_sec": 2,
  "explanation": "Reference solution explanation.",
  "reference_code": "Reference source code goes here.",
  "tests": [
    {"input": "sample input", "expected_output": "sample output", "is_sample": true},
    {"input": "hidden input", "expected_output": "hidden output", "is_sample": false}
  ]
}
```

The importer publishes the supplied complete problem transactionally, replacing
tests only on an existing draft. Published problems are not overwritten. Reference
solutions remain subject to the existing solution-unlock rules. Bundles must use
standard input/output and the judge's exact-output comparison; interactive or
custom-checker Codeforces problems are not supported.

Development only: the subprocess judge executes code on the host and is not a security sandbox. Use trusted submissions locally. The in-memory queue/channel layer requires one server process.
