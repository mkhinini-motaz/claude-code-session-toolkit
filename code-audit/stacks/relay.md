# Socket relay (Node, Socket.IO)

## Extra facts for the brief

- The folders of every app that connects, so the agent can grep their listeners.
- The memory limit the relay runs under in production, and the load target (live sockets).
- Example env files only. A read of a real env file is refused, and that is correct.

## Sections

1. METRICS: tests, advisories, lint under a scratch config when the repo has none, file sizes.
2. EVENT CONTRACT: a table of every event the relay emits and which apps listen, and every event apps emit and
   whether the relay handles it. Events with no listener, listeners with no emitter.
3. ISOLATION: can one tenant, role or user join or receive another's room or channel. Auth on connect, session
   end, token renewal.
4. FAILURE: handlers for uncaught errors and stop signals, reconnection after a restart, what a Redis outage does.
5. LOAD: connections opened per socket (Redis, timers), what breaks first at the load target, unused adapters or
   clients.
6. REMOVE AND SIMPLIFY: handlers that are near copies, dead code, stale docs and comments, env variables read
   and missing from the example file.
7. PACKAGES AND BUILD: majors behind and what an upgrade rewrites, the Node version pinned where, whether CI runs
   the tests before the image is built.

## False positives seen

- An adapter that looks used because it is configured: check for room broadcasts and for a second instance.
- An event with no listener may be a missing listener in an app, not a dead event. File it as a question.
