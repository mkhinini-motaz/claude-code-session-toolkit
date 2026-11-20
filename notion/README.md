# notion

Two Python scripts (standard library only) that read and write Notion pages over Notion's REST API. `notion get` prints a page as compact Markdown, and `--part NAME` prints one section. Writes change one section, one block or one property, so an agent never has to quote the old text of a whole page.

Measured on 10 task pages (20 Nov 2026): `notion get` returned about 28% of the characters of the MCP connector's `notion-fetch` for a whole page, and about 5% with `--part`.

## Install

    ./install.sh notion    # copies notion and notion-push to ~/.claude/bin

`notion` loads `notion-push` from its own folder, so keep the two together.

## Token

1. Create an internal integration at notion.so/profile/integrations.
2. Share each top page with it: the page's ... menu, then Connections. The integration sees only shared pages and their children.
3. Store the token. On macOS: `security add-generic-password -a "$USER" -s notion-api -w` (it prompts for the value). Elsewhere, or to override: `export NOTION_TOKEN=...`.

The scripts read the token in-process and never print it.

## Usage

    notion get <page> [--part NAME]... [--props]
    notion put <page> NAME [file|-]       replace one section's body with Markdown
    notion add <page> NAME [file|-]       insert at the top of one section
    notion edit <page> "old" "new"        change text in the one block or table cell that holds it
    notion set <page> Name=Value ...      change properties
    notion query <database> [Prop=V | Prop!=V]... [--cols A,B]
    notion new <database|page> "Title" [Name=Value ...] [file|-]
    notion search <words>                 titles only
    notion trash <page>
    notion-push <file.md | -> <page> [--append | --replace] [--dry-run]
    notion --self-test; notion-push --self-test     offline tests, no token needed

`notion-push` converts Markdown to Notion blocks: headings, lists, to-dos, tables, code, quotes, dividers, callouts (`> 📍 text`) and toggles (`▸ text`), sent in batches of 100 blocks. Tables, toggles and lists over 100 items also go in batches of 100. Text is split by Notion's own length count (an emoji counts 2). `notion-push` flags are checked: an unknown one stops with usage instead of appending.

`notion put` and `notion-push --replace` write the new blocks first and delete the old ones after, so a refused write loses nothing. Page IDs and URLs are accepted, including a URL that ends in a year or `?v=`. Requests are retried on timeouts, resets, 409, 429 and 5xx, writes included: if a timeout hits after Notion applied an append, check the page before rerunning.

Known gaps in this version: `notion` keeps an unknown `--flag` as a positional argument (`notion trash <id> --dry-run` trashes the page), and `notion put <id> <part>` with no file and empty input clears the part. Pass the file or `-` every time.

## IPv4 first

Both scripts sort IPv4 addresses before IPv6 when they connect. On one network, IPv6 connections to api.notion.com hung for over 100 seconds before failing over. The patch is three lines at the top of `notion-push`; remove them if you do not need it.

## Limits

- Page mentions become plain links when a block's text is rewritten.
- Only four callout emoji map to colours (📍 blue, ✅ green, ❓ yellow, ⚠️ red); others are gray.
- `search` matches titles only. Comments, views and page history are not covered.

## Requirements

Python 3.9 or later. macOS `security` for the keychain; on Linux, `NOTION_TOKEN` is the only option.
