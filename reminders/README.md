# reminders

A SessionStart hook that shows reminders whose date has come. Each row can be tied to a folder, so a reminder for one project shows only in sessions started inside it.

## Install

    ./install.sh reminders    # copies reminders.py to ~/.claude/hooks

Merge the snippet that `install.sh` prints into `~/.claude/settings.json` (SessionStart, matcher `startup|clear`).

## Usage

Create `~/.claude/reminders.tsv`. One row per line, three tab-separated fields: date (`YYYY-MM-DD`), folder (`~` allowed, empty for every session), text. Lines starting with `#` and empty lines are skipped. A row is due when its date is today or earlier and the session's folder is the row's folder or inside it.

    # date<TAB>folder<TAB>text
    2030-01-15<TAB>~/work/app<TAB>Renew the staging certificate

When a row is due the hook shows "Due: <date>: <text>" and asks Claude to say so in its first reply and to delete the row once it is done. Test with a fixed date:

    echo '{"cwd":"'$HOME'/work/app"}' | REMINDERS_TODAY=2030-01-16 python3 reminders/reminders.py

## Requirements

Python 3.
