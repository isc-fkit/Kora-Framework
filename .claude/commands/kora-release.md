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
5. ✋ **Confirm** → write `version.json` + prepend the CHANGELOG entry + **sync the version label on the
   landing `index.html`** (the hero `.badge` — must match) + commit.
6. **Ask: Merge or Deploy?** (AskUserQuestion) — **[Deploy from `release`]** (Pages deploys web from
   release) or **[Merge `release`→`main`]** (push release, then ff-merge into main + push main). Never
   force a non-ff merge.
7. **Tag = version** (must MATCH `version.json`, no codename suffix): `git tag vX.Y.Z && git push origin vX.Y.Z`.
8. **GitHub Release + release notes** (if `gh` available): `gh release create vX.Y.Z --title "Kora-1 vX.Y.Z"
   --notes "<the CHANGELOG vX.Y.Z entry>"`.
9. **Version consistency** — verify the SAME `vX.Y.Z` shows in: `version.json` · CHANGELOG header · landing
   badge · git tag · GitHub Release. Fix any mismatch. Then report: **web (Pages) deployed**; app users get
   it via `/kora-update`.

Never push without the confirmation gate. Keep secrets out of commits.
