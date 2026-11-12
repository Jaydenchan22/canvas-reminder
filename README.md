# Canvas Reminder

Get push notifications for your Canvas assignments, quizzes and exams on your phone,
tablet and laptop, without needing a Canvas API token.

It reads your personal **Canvas calendar feed** and sends a daily digest through
[ntfy](https://ntfy.sh), a free push-notification service with apps for iOS and Android
and a web app for desktop. It was built for UBC but works with any school that uses Canvas.

```
Canvas calendar feed ──▶ reminder.py ──▶ ntfy.sh ──▶ phone / tablet / laptop
        done.txt (filter) ──┘   ▲
                       scheduler (8 AM + 6 PM daily)
```

Example notification:

```
4 due in the next 7 days

EXAMS / TESTS
- Fri Nov 20 6:50 PM | CPEN 211 Test 5

ASSIGNMENTS
- TODAY 11:59 PM | MATH 253 WW Assignment 7
- Tomorrow 9:00 AM | CPEN 221A Lab 7
- Fri Nov 13 11:59 PM | CPEN 221A Project Milestone 3
```

## Features

- **Daily digest:** everything due in the next 7 days (configurable).
- **Evening urgent alert:** sent only if something is due within 24 hours.
- **Exams first:** items with "midterm", "exam" or "test" in the title go at the top, and an exam within 3 days makes the notification high priority.
- **Hide finished work:** list it in `done.txt`. The calendar feed can't see what you've submitted.
- **No API token needed:** useful if your school doesn't let students generate one.

## Setup

### 1. Get the code and install
Requires **Python 3.10+** (on Windows, tick "Add python.exe to PATH" when installing).

```powershell
git clone https://github.com/<your-username>/<this-repo>.git
cd <this-repo>
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt     # macOS/Linux: .venv/bin/pip install -r requirements.txt
```

### 2. Create your private config
```powershell
copy .env.example .env          # macOS/Linux: cp .env.example .env
copy done.example.txt done.txt  # macOS/Linux: cp done.example.txt done.txt
```
Both files are git-ignored, so they never get uploaded.

### 3. Add your Canvas calendar feed
In Canvas, open **Calendar**, then click **Calendar Feed** at the bottom right and copy the URL.
Paste it into `CANVAS_ICS_URL=` in `.env`.

> Treat this URL like a password. Anyone who has it can see your calendar.

### 4. Set up notifications (ntfy)
1. Choose a long, random topic name, e.g. `canvas-reminder-x8f2k9q7m3`, and put it in `NTFY_TOPIC=` in `.env`.
   ntfy topics are public by name, so **a hard-to-guess name is what keeps your notifications private**.
2. Install **ntfy** on your devices (App Store / Google Play), or open https://ntfy.sh/app in a desktop browser and allow notifications.
3. Subscribe to your topic on each device.

### 5. Test it
```powershell
.\.venv\Scripts\python reminder.py --test       # sends a test notification
.\.venv\Scripts\python reminder.py --dry-run    # prints the digest without sending
```

### 6. Schedule it

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File .\schedule_tasks.ps1
```
This creates two tasks, `UniReminder Digest` (8 AM) and `UniReminder Urgent` (6 PM). If your computer
was off or asleep at those times, they run shortly after you log in.
To remove them: `Unregister-ScheduledTask -TaskName "UniReminder*" -Confirm:$false`

**macOS / Linux:** run `crontab -e` and add the lines below, using absolute paths:
```
0 8  * * * cd /path/to/repo && .venv/bin/python reminder.py
0 18 * * * cd /path/to/repo && .venv/bin/python reminder.py --urgent
```

## Usage

| Command | What it does |
|---|---|
| `python reminder.py` | Send the digest now |
| `python reminder.py --urgent` | Send only if something is due within 24h |
| `python reminder.py --dry-run` | Preview without sending |
| `python reminder.py --test` | Send a test notification |

**Finished something?** Add part of its title to `done.txt`, e.g. `WW Assignment 7`.
- Matching is case-insensitive and checks only the title, not the course name.
- Make the keyword specific: `Lab` would hide every lab.
- Notifications already sent don't change; the next run reflects your edit.

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `CANVAS_ICS_URL` | (required) | Your Canvas calendar feed URL |
| `NTFY_TOPIC` | (required) | Your private ntfy topic name |
| `NTFY_SERVER` | `https://ntfy.sh` | Change this if you self-host ntfy |
| `DAYS_AHEAD` | `7` | How many days ahead the digest looks |
| `TIMEZONE` | `America/Vancouver` | Your IANA timezone |

## Limitations

- **Submissions aren't detected.** The feed has no submission status, so use `done.txt`.
- **Only exams on your Canvas calendar appear.** Exams listed only in a syllabus won't show up.
- **Your computer must be on.** The scheduler runs locally; missed runs happen at your next login.
- **Course names are shortened** for UBC-style codes (e.g. `CPEN 221A`). Other schools show the course name as Canvas provides it.

## License

MIT. See [LICENSE](LICENSE).
