# notion-task-pages

A skill with the section order and writing rules for the body of a Notion task page: one-line goal, a Current state callout, Done means, a Decisions table, Open questions, Context, and a History toggle. Updates rewrite Current state and Decisions and put the dated log in History.

## Install

    ./install.sh notion-task-pages    # copies SKILL.md to ~/.claude/skills/notion-task-pages

Or install the whole repo as a plugin. The skill pairs with `notion/`: its `notion` command reads and writes a page one section at a time.

## Usage

Claude loads the skill before it creates a task page or rewrites a page body. Keep your database and page IDs in your project's own notes, not in the skill.

## Requirements

None for the skill itself; the pages themselves need a Notion integration (see `notion/`).
