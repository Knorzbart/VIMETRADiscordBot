# VIMETRADiscordBot Agent Instructions

## Start map

`AGENTS.md` is the concise start map. No additional repository-owned
entrypoint is declared yet; perform bounded read-only discovery and record
a reviewed `N/A` instead of inventing a command name.

<!-- BEGIN MANAGED REPOSITORY OPERATING CONTRACT -->
source_repository: Knorzbart/CodexRulesAndSkills
source_path: global/abstract_global/AGENTS.md
source_commit: b625084fdf2e0ef555d605a5b2f3c99054e3e65d
source_revision: AEH-RULES-008
surface_sha256: b306ca8927c3101967471cbbb82d17171d9abfa8ad5cac256a075190df0549f1
managed_payload_sha256: 067923fa4e45897921773a843f60962ae9a76dbb29c691177c2075ab7db749f2
managed_envelope_sha256: b98db8dcbb01a09dde682f71b7bfe76beb6bf20193fa98b1dabb9d3766f31d1f

## Authority routing for this repository

Existing explicit field authorities remain authoritative and are not
overwritten by this deployment. For fields without an existing explicit repository authority, GitHub Issues owns the stable work item, issue state, labels and milestone. GitHub Projects is only a conflict-safe synchronized view unless the pre-existing repository instructions explicitly make a Project field authoritative.

## Repository navigation and work-item authority

- Every stable work item and mutable lifecycle field has exactly one named
  authority. A project board is optional: it is either that authority or a
  conflict-safe synchronized view, never a second manually maintained to-do.
- Every mutating lane uses one branch, one isolated worktree and one writer.
  Parallel lanes also isolate ports, caches and outputs. A chat is context,
  never merge, release, rollback or lifecycle authority.
- Every repository declares its own entrypoints. Read `AGENTS.md` and the one
  concise repository-relative start map it names; `AGENTS.md` may itself be
  that map. Prefer repo-owned commands and never impose remembered filenames.
- Preflight is risk-based: verify Git/worktree/writer identity and run each
  relevant bounded, preferably read-only doctor, lock/lease check and baseline
  smoke, or retain a reviewed `N/A`. Reuse expensive evidence only with exact
  input, artifact and environment hashes.
- Start repository-local and unprivileged without unnecessary questions.
  Escalate narrowly only for protected, irreversible, credentialed, paid or
  production actions. Missing external checks remain named evidence debt and never count as passed.
  Never commit secrets.
- Skill and rule synchronization is a deployment: compare source and target,
  pin exact revisions and hashes, validate both sides, reject downgrade or
  silent removal, and activate atomically. Registry publication, global installation and target-project adoption are distinct states.
- Keep one concise repository-relative start map without duplicate truth.
- Delivery speed is governed by `AEH-R008`: ship the smallest independently
  usable reversible slices and continue an independent lane while another
  waits, without weakening quality, safety, artifact, performance, rollback or
  truthful-evidence gates.
<!-- END MANAGED REPOSITORY OPERATING CONTRACT -->
