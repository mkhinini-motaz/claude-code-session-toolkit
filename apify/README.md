# apify

Apify's REST API as one short command per job, printing compact tables instead of the Apify MCP connector's full JSON. Python standard library only.

Measured on a real run (20 Nov 2026): three public job-listing searches of 20 jobs each, USD 0.043 in total. `apify run ... --fields` printed 20 jobs with 7 fields in about 4,000 characters; the full JSON of the same 20 jobs is over 20,000.

## Install

    ./install.sh apify    # copies apify to ~/.claude/bin

## Token

`APIFY_TOKEN`, else the macOS keychain item `apify-api` (`security add-generic-password -a "$USER" -s apify-api -w`), else the file `~/.apify_token`. The token is read in-process and never printed.

## Usage

    apify search <words>                    Store actors: id, title, users, rating, pricing
    apify schema <actor>                    input fields: name, type, default, required (cached 7 days)
    apify run <actor> <input.json|-> --max-usd N [--fields a,b.c,d:300] [--limit N] [--max-items N] [--timeout SEC]
    apify items <dataset|run id> [--fields ...] [--limit 50] [--offset 0] [--json]
    apify runs [--limit 10]
    apify --self-test

`--fields` takes dot paths, and `:N` cuts a value to N characters. Without `--fields`, `items` prints the field list with types and average sizes, so you can pick fields before reading. `--json` prints the full items for piping.

`--max-usd` is required. It is sent as `maxTotalChargeUsd`, which stops pay-per-event actors at that amount. Actors billed by compute time do not stop there, so check `apify schema` and the Store price first.

A GET is retried on 429, 5xx and network errors; a POST is never retried, because it could start a second paid run. An empty schema is not cached.

Both this script and `notion-push` try IPv4 before IPv6: on one network, IPv6 connections hung.

## Requirements

Python 3. macOS `security` for the keychain (macOS only), or `APIFY_TOKEN` or `~/.apify_token` anywhere.
