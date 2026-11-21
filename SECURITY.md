# Security

## Report a vulnerability

- Open the **Security** tab of this repository and choose **Report a vulnerability**. The report stays private.
- If that button is missing, open an issue titled "Security contact" with no details. The maintainer will reply and arrange a private channel.

Do not post details, tokens or proof-of-concept output in a public issue.

## In scope

- `notion` and `apify`: a token written to a log, a file or the screen, or sent to a host other than the service.
- `apify`: a run that ignores its spending cap.
- Hooks (`notes`, `img-shrink`, `agent-watch`, `compact-restore` and the rest): a hook that runs unexpected commands, or reads or writes outside the paths its README names.
- `install.sh`: any edit to `settings.json`, or an overwrite of an existing file.
- `browse`: a page that makes it run code on your machine.

## Out of scope

- Findings that need you to run code you wrote yourself.
- Weaknesses in Claude Code, Node, Python or GitHub themselves. Report those to their owners.
