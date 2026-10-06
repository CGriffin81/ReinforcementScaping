# Agent Interaction

## Metadata

- Interaction ID: m001-github-repo-and-local-infra
- Timestamp CST: 2026-10-05 ~21:29:00 CST (estimated: the first command run for this prompt reported 21:30:12 local Central time)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: `1e7291a` (initial commit, which includes the first version of this record); this record was closed out in the following commit

## Full Prompt

> Look in D:\Promethean\promethean\docs\agent-interactions for context on how to track our interactions. Let me know if you need more information about that.
>
> Create a new repo in my github. Look in D:\Promethean\promethean\ if you need more context about that.
>
> It ok to run MariaDB in Docker with no root password.

Follow-up prompts in the same thread, all about the GitHub step:

> Check the terminal output.

> I have gitbash. Let's use that instead of github cli.

> Leave it. We're authenticated. Create the repo.

## Response Summary

- **Policy:** read the Promethean `CLAUDE.md`, the full steering doc
  `D:\Promethean\.kiro\steering\ai_log_requirements.md`, and an example record
  (`m022-credentials-access-method-fix.md`). Adopted the policy as
  `docs/ai-log-requirements.md`, dropping the Promethean-specific sections
  (Pulumi deployment records, capstone paper format). Defined milestone
  numbering for this project: `m000` is planning, `m00N` is ROADMAP week N.
  Wrote records for the two earlier interactions in this session, plus this one.
- **GitHub:** found the account `CGriffin81` from the Promethean remote and Git
  Credential Manager. The GitHub CLI wasn't installed, so I installed it via
  winget. It isn't authenticated, and signing in is the user's step (Claude
  doesn't handle credentials), so repo creation was blocked at first. Made the
  local initial commit with author `CGriffin81 <calebpgriffin81@gmail.com>`, the
  same identity as the Promethean commits.
  - *Terminal check:* the user's `gh auth login` failed with "not recognized"
    because their terminal tab was opened before the CLI was installed, so its
    PATH was stale. Their `git push` failed only because no remote existed yet.
    Their `git add .` was harmless, and the working tree was clean at `1e7291a`.
    Suggested using the full path or a new tab.
  - *Git Bash instead of the CLI:* explained that git can't create a repo on
    GitHub by itself, gave web-UI steps as the alternative, and asked whether to
    uninstall the CLI. The user kept it.
  - *Repo created:* after the user authenticated `gh` themselves (keyring, account
    CGriffin81), ran
    `gh repo create CGriffin81/ReinforcementScaping --private --source . --remote origin --push`.
- **MariaDB:** added `infra/docker-compose.db.yml`: MariaDB 11.4, empty root
  password, port bound to `127.0.0.1:3306` only, initialized from the server's
  `global.sql`. Started it; it came up healthy with database `global` (tables
  `members`, `worlds`).
- **Server run:** started the server jar against MariaDB. The first launch took
  418 s: `GEDB.populateInitialPriceIndex` runs one autocommitted SQLite insert per
  tradeable item (seen via `jstack` while startup seemed stalled). After that it
  logged "2009Scape started", the built-in bots began ticking, it listened on
  `:::43595`, and the log showed no exceptions. Stopped the server afterwards.
- **New finding (G3):** the GE price index is seeded from each item's
  high-alchemy value (`GEDB.kt`), not real 2009 prices, so the fixed price table
  has to be a deliberate, documented snapshot.
- Added `CLAUDE.md` (project steering for future sessions) and
  `docs/decision-log.md`.

## Documentation Changes

- Added `CLAUDE.md`.
- Added `docs/ai-log-requirements.md`.
- Added `docs/decision-log.md`.
- Added `docs/agent-interactions/m000-initial-roadmap.md`,
  `m000-open-decisions-resolved.md`, and this record.
- Updated `ROADMAP.md`: week-1 server run checked off, with the first-launch time
  and the all-interfaces port note.

## Code Changes

- Added `infra/docker-compose.db.yml`. It's configuration, not application code.

## Infrastructure Changes

- Installed GitHub CLI 2.102.0 via winget.
- Created the Docker container `rlscape-mariadb` (MariaDB 11.4), the volume
  `infra_rlscape-db`, and the network `infra_default`. The port is published on
  127.0.0.1:3306 only.
- The first server launch created `server/Server/data/eco/grandexchange.db` and
  `server/Server/data/playerstats/player_stats.db`. Both are inside the
  git-ignored upstream clone.
- Set repo-local git identity: `user.name=CGriffin81`,
  `user.email=calebpgriffin81@gmail.com`.
- Created the GitHub repo `https://github.com/CGriffin81/ReinforcementScaping`
  (private) with remote `origin`, and pushed `main` (tracking `origin/main`).
  The GitHub CLI was authenticated by the user, not by Claude.

## Decisions

- **User decision:** the AI-interaction tracking follows the Promethean
  `docs/agent-interactions` convention.
- **User decision:** create a new repo in the user's GitHub account.
- **User decision:** MariaDB runs in Docker with no root password.
- **Agent decision (reversible default):** the new repo is **private**. Making it
  public would publish the work; that's the user's call.
- **Agent decision (reversible default):** repo name `ReinforcementScaping`,
  matching the local folder.
- **Agent decision:** bind MariaDB to localhost only, since the root password is
  empty.
- **Agent recommendation (pending):** restrict the game server's listening
  address to localhost before leaving it running, because `noauth_default_admin`
  is on.

## Validation

- `docker inspect` health is `healthy`. `SHOW DATABASES` lists `global`, and
  `SHOW TABLES` in it returns `members` and `worlds`.
- The server log ends with "2009Scape started in 418045 milliseconds" and contains
  zero `exception` or `error` matches. Port 43595 was listening.
- Before the user signed in, `gh auth status` reported "You are not logged into
  any GitHub hosts". After they signed in, it reported "Logged in to github.com
  account CGriffin81 (keyring)".
- `gh repo view` reports `PRIVATE`, with default branch `main`.
  `git ls-remote origin main` returns `1e7291a73a1ea330d75474d94186db3fd5c10f7c`,
  matching the local `HEAD`.

## Follow-Up

- Next week-1 work, which is the first real code and should get its own record:
  the configurable tick patch (G1), a minimal `RLBridge` (G2), GE price logging
  (G3), and the Python `uv` skeleton.
- Decide how server modifications are tracked: an overlay or patch directory in
  this repo, or a separate fork repo.
