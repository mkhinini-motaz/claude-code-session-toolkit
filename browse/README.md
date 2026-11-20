# browse

A scripted web walk: one Bash call runs a whole browser check in headless Chrome, so an agent spends one call instead of 10 to 20 Playwright MCP calls.

## Install

    ./install.sh browse    # copies browse to ~/.claude/bin

## Usage

    browse [options] steps.txt      # or - for stdin
    browse --self-test
    browse --help                   # prints the usage

One step per line, `#` comments and blank lines ignored, multi-word arguments in double quotes:

    goto <url|/path>    click <text|css=sel>    fill <label|placeholder|css=sel> <value>    press <key>
    expect <text>       expect-not <text>       wait <ms>                                   shot <name>

Options: `--base URL`, `--width PX` (1280; 390 for a phone), `--lang CODE` (sets Accept-Language and a `lang` cookie on the base URL), `--out DIR` (default `browse-<uid>` under the system temp folder)and `--timeout MS` (5000). An unknown `--option` stops with exit 2.

It prints `ok N step` for each step and stops at the first `FAIL` (saving `fail.png`, exit code 1). Then it prints the console errors, the failed (4xx/5xx) requests and the screenshot paths. It never prints page HTML.

`click` skips a match that another element covers (a modal over the page) and takes the next visible one.

Use the Playwright MCP to explore a page, or when a step kind is missing.

## Requirements

macOS, Node.js and an installed Google Chrome. On first use it installs `playwright-core` 1.49.1 into `~/.cache/browse-playwright`; it never downloads a browser.
