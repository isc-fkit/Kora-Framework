---
description: Automate a release — propose the next version, generate the CHANGELOG from commits, then bump + commit + push (deploy). Maintainer only.
---

The user invoked `/kora-release` — automate a release (**MAINTAINER only**).

Read and execute `workflows/12-release.md` following `CLAUDE.md`, automating these:

1. **Bước 0 — guard:** verify `.maintainer` exists at repo root. If NOT → stop politely (do NOT bump /
   push); suggest `/kora-update` (get latest) or `/kora-export-knowledge-base` (backup). Maintainer
   only.
2. **Propose version:** read current `version.json`; suggest the next **semantic** version (keep
   codename "Kora-1"); ask **[patch] / [minor] / [major]** via AskUserQuestion.
3. **Auto CHANGELOG:** generate the new entry **from `git log <last-tag-or-version>..HEAD`** (group by
   type: feat/fix/docs…); show it for review/edit.
4. **Plan:** list what ships (CORE changed), note any migration step, and whether installer zips need
   regenerating (if `install.command`/`uninstall.command` changed → re-zip `*.command.zip`).
5. ✋ **Confirm** → write `version.json` + prepend the CHANGELOG entry + commit + `git push origin <branch>`
   (deploy). Optionally `git tag v<version>`.

Never push without the confirmation gate. Keep secrets out of commits.
