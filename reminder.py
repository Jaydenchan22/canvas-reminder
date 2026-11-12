"""UBC Canvas reminder.

Reads your Canvas calendar feed (.ics) and pushes a notification to all
your devices via ntfy. Items with exam-like titles (midterm, exam, test)
are listed first and raise the priority.

Usage:
    python reminder.py              # send digest (items due in next DAYS_AHEAD days)
    python reminder.py --dry-run    # print the digest, don't send
    python reminder.py --urgent     # only send if something is due within 24h
    python reminder.py --test       # send a test notification
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from icalendar import Calendar

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

TZ = ZoneInfo(os.getenv("TIMEZONE", "America/Vancouver"))
ICS_URL = os.getenv("CANVAS_ICS_URL", "").strip()
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "").strip()
DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "7"))
DONE_FILE = ROOT / "done.txt"


@dataclass
class Item:
    title: str
    due: datetime
    course: str = ""
    url: str = ""
    is_exam: bool = False


# ---------- data sources ----------

def to_local(value) -> datetime:
    """Convert an iCal date/datetime to a timezone-aware local datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=TZ)
        return value.astimezone(TZ)
    # All-day event (plain date): treat as end of that day.
    return datetime.combine(value, time(23, 59), tzinfo=TZ)


COURSE_RE = re.compile(r"\b([A-Z]{3,4})[_ ]?V?\s+(\d{3}[A-Z]?)")
# Leftover section tags in titles, e.g. "(CPEN_V 221A A_101 2026W1)"
SECTION_TAG_RE = re.compile(r"\s*\([^()]*\d{4}W\d\)")
# Titles that count as exams/tests (whole words, case-insensitive)
EXAM_RE = re.compile(r"\b(midterms?|exams?|examination|tests?)\b", re.IGNORECASE)


def split_course(summary: str) -> tuple[str, str]:
    """Canvas summaries look like 'Lab 7 [CPEN_V 221A/B 101 2026W1]' -> ('Lab 7', 'CPEN 221A')."""
    title, course = summary.strip(), ""
    if title.endswith("]") and "[" in title:
        title, _, raw = title.rpartition("[")
        m = COURSE_RE.search(raw)
        course = f"{m.group(1)} {m.group(2)}" if m else raw.rstrip("]").strip()
    return SECTION_TAG_RE.sub("", title).strip(), course


def fetch_canvas() -> list[Item]:
    if not ICS_URL:
        print("CANVAS_ICS_URL not set in .env - skipping Canvas.", file=sys.stderr)
        return []
    req = urllib.request.Request(ICS_URL, headers={"User-Agent": "uni-reminder/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        cal = Calendar.from_ical(resp.read())

    items = []
    for ev in cal.walk("VEVENT"):
        start = ev.get("DTSTART")
        if start is None:
            continue
        title, course = split_course(str(ev.get("SUMMARY", "Untitled")))
        items.append(Item(title, to_local(start.dt), course, str(ev.get("URL", "")),
                          is_exam=bool(EXAM_RE.search(title))))
    return items


def load_done() -> list[str]:
    """done.txt: one keyword per line; any item whose title contains it is hidden."""
    if not DONE_FILE.exists():
        return []
    lines = DONE_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip().lower() for l in lines if l.strip() and not l.startswith("#")]


# ---------- formatting / sending ----------

def when(due: datetime, now: datetime) -> str:
    days = (due.date() - now.date()).days
    clock = due.strftime("%I:%M %p").lstrip("0")
    if days == 0:
        return f"TODAY {clock}"
    if days == 1:
        return f"Tomorrow {clock}"
    return due.strftime("%a %b %d ") + clock


def build_digest(items: list[Item], now: datetime) -> str:
    exams = [i for i in items if i.is_exam]
    work = [i for i in items if not i.is_exam]
    lines = []
    if exams:
        lines.append("EXAMS / TESTS")
        lines += [f"- {when(i.due, now)} | {i.course} {i.title}" for i in exams]
        lines.append("")
    if work:
        lines.append("ASSIGNMENTS")
        lines += [f"- {when(i.due, now)} | {i.course} {i.title}" for i in work]
    return "\n".join(lines).strip()


def send(title: str, body: str, priority: str = "default", tags: str = "books") -> None:
    if not NTFY_TOPIC:
        sys.exit("NTFY_TOPIC not set in .env")
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Tags": tags},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


# ---------- main ----------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--urgent", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    if args.test:
        send("Uni Reminder test", "If you see this, notifications work!", tags="white_check_mark")
        print("Test notification sent.")
        return

    now = datetime.now(TZ)
    window = timedelta(hours=24) if args.urgent else timedelta(days=DAYS_AHEAD)
    done = load_done()

    items = [
        i for i in fetch_canvas()
        if now <= i.due <= now + window
        and not any(k in i.title.lower() for k in done)
    ]
    items.sort(key=lambda i: i.due)

    if not items:
        print("Nothing due in this window.")
        if args.urgent:
            return
        body = f"Nothing due in the next {DAYS_AHEAD} days."
    else:
        body = build_digest(items, now)

    has_exam_soon = any(i.is_exam and i.due - now <= timedelta(days=3) for i in items)
    if args.urgent:
        title, prio, tags = f"Due within 24h ({len(items)})", "high", "warning"
    else:
        title = f"{len(items)} due in the next {DAYS_AHEAD} days"
        prio, tags = ("high", "rotating_light") if has_exam_soon else ("default", "books")

    print(f"{title}\n\n{body}")
    if not args.dry_run:
        send(title, body, prio, tags)
        print("\nSent.")


if __name__ == "__main__":
    main()
