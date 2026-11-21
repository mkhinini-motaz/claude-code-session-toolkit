---
name: notion-task-pages
description: Section order and writing rules for a Notion task page in any project. Load before creating a task page or rewriting its body, its Current state or its Decisions.
---

# Notion task pages

Rules for the body of one task page. Where the database, IDs and write calls live depends on the project: keep them in that project's own notes. Read and write pages with the Notion tools you have: a Notion connector, or the full toolkit's `notion` command line (get, put, add, edit, set, new, query, search). With neither, write the page body as Markdown for the user to paste.

## Order of sections

1. A one-line goal.
2. 📍 Current state – <date>: a blue_bg callout with 1–3 bullets on where it stands, what's left, and what blocks it.
3. Done means: 3–5 bullets.
4. Decisions: a table with the columns Decision | Since | Replaces. The new value leads the Decision cell; Replaces holds the old value struck through, with its date.
5. Open questions: each with who decides.
6. Context: short, explaining why the task exists.
7. History: a toggle at the bottom, newest first.

## On every update

- Rewrite Current state and Decisions. Never add a dated status paragraph to the body.
- Put the dated log in History: what happened, commits, migrations, endpoints, test names.
- When a decision changes, update the Decisions row. Move the old value to History as "Superseded <date>: <old> → <new>". No superseded value may stay above History, except struck through in the Decisions table's Replaces column.
- Take the date from `date`, never from memory.

## Writing

- Never write counts or status in prose when a property, relation or rollup already holds them.
- Keep sentences under about 20 words, with one idea per bullet. Put the key fact first.
- Bold at most one phrase per section: the fact a skimmer must not miss.
- Callouts have fixed meanings: 📍 blue_bg = current state, ✅ green_bg = decided, ❓ yellow_bg = open, ⚠️ red_bg = blocker. Use no other emoji or colour in page bodies. With `notion` (pages its integration reaches), write a callout as `> 📍 title` and a toggle as `▸ title`, content indented two spaces: the script sets the colour from the emoji.
- Code identifiers belong in History, never inside the sentence that states a decision.
- An older page in another layout converts to this one on its next update.
