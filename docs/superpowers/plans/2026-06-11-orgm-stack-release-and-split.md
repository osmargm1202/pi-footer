# ORGM Stack Release and Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release `pi-footer` v0.2.7, document ORGM stack coupling across packages, and start the package split path.

**Architecture:** Keep `pi-footer` as real Zentui fork and UI owner. Keep ORGM package dependencies soft and documented. Start split with clear scope boundaries before extracting code.

**Tech Stack:** Pi extension packages, npm package metadata, GitHub releases, markdown docs.

---

### Task 1: Release pi-footer v0.2.7

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Create: `docs/releases/v0.2.7.md`

- [ ] Bump npm version to `0.2.7` without tag.
- [ ] Create release notes documenting fork rename, ORGM title/caveman line, stale ctx fix.
- [ ] Run `npm run verify` and `npm run pack:check`.
- [ ] Commit, tag `v0.2.7`, push branch and tag.
- [ ] Create GitHub release from notes.

### Task 2: Update stack docs

**Files:**
- Modify README in `pi-footer`, `pi-harness`, `pi-mem`, `pi-caveman`.

- [ ] Ensure each README contains install loop:

```bash
for pkg in pi-mem pi-caveman pi-harness pi-footer; do
  pi install git:github.com/osmargm1202/$pkg
done
```

- [ ] Document each package produces/consumes.
- [ ] Commit and push changed repos.

### Task 3: Start split path

**Files:**
- Create or modify split spec in `pi-harness` docs.
- Optionally create GitHub repos if split package names are available.

- [ ] Confirm repo availability for `pi-ask`, `pi-todo`, `pi-banner`, `pi-title`.
- [ ] Write split scope doc: source modules, package responsibilities, dependency graph.
- [ ] If safe, create empty repos with README skeletons.
- [ ] Do not extract code until scope is committed.
