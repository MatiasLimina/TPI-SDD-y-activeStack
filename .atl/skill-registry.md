# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## Project Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Build features/fix bugs test-first, red-green-refactor, integration tests | tdd | .agents/skills/tdd/SKILL.md |
| Writing Python tests, pytest fixtures, mocking, TDD | python-testing-patterns | .agents/skills/python-testing-patterns/SKILL.md |
| FastAPI APIs, routers, Pydantic, async operations | fastapi-python | .agents/skills/fastapi-python/SKILL.md |
| Any Postgres schema/migration/index/constraint/query/RLS work | supabase-postgres-best-practices | .agents/skills/supabase-postgres-best-practices/SKILL.md |
| Auth systems, JWT, RBAC, session mgmt, securing APIs | auth-implementation-patterns | .agents/skills/auth-implementation-patterns/SKILL.md |
| Review/validate a change's spec scenarios against the KB, after propose/update and before apply | revisar-escenarios | .agents/skills/revisar-escenarios/SKILL.md |
| Check Alembic migration numbering across remote branches, before opening/merging a PR with a migration | revisar-migraciones | .agents/skills/revisar-migraciones/SKILL.md |
| Review a PR / branch diff against repo standards and the change's spec (main use: PR review before approving) | code-review | .agents/skills/code-review/SKILL.md |
| Frontend tests (C-14..C-16): Vitest, mocks, fake timers, hooks, jsdom environment, coverage | vitest | .agents/skills/vitest/SKILL.md |

All skills are installed **at project level** in `.agents/skills/` (versioned; third-party ones pinned in `skills-lock.json`; `npx skills add <repo> --skill <name>` without `-g`). Paths above are relative to the project root.

`revisar-escenarios` is the project's **own** skill (authored 2026-10-16 with `skill-creator`, not installed from a repo, so it has no entry in `skills-lock.json`). Purpose: report-only review of a change's GIVEN/WHEN/THEN scenarios against RN/DD/SU rules and the change scope in `CHANGES.md`; output goes to `openspec/changes/<change>/revision-escenarios.md`. Usage evidence: `docs/skills-mcp/evidencias/skill-evals/`.

`revisar-migraciones` is the project's second **own** skill (authored 2026-11-03, no `skills-lock.json` entry). Purpose: report-only check that hand-numbered Alembic revisions on every `origin` branch follow `origin/main`'s head; the work is done by `scripts/revisar_migraciones.py` (stdlib only, reads branches via git without checkout).

`code-review` (mattpocock/skills, pinned in `skills-lock.json`, installed 2026-11-03) is the skill for **reviewing pull requests** before the other team member approves them (every change enters `main` through a PR; see `docs/equipo/reparto-de-tareas.md`). It reviews `git diff <fixed-point>...HEAD` along two separate axes, run as two parallel read-only sub-agents: **Standards** (repo rules + a Fowler code-smell baseline) and **Spec** (does the diff implement what the change's spec asked for). How to use it on a PR:
1. Check out the PR branch (`gh pr checkout <n>`) and `git fetch origin`.
2. Invoke the skill with fixed point `origin/main` and the change folder as spec path: `openspec/changes/<change>/` or, since the archive runs on the change branch before merge, `openspec/changes/archive/<fecha>-<change>/` (proposal, design, delta specs, tasks), plus the change block in `CHANGES.md`.
3. The skill asks for an issue tracker and suggests `/setup-matt-pocock-skills`: this project does not use one (specs live in OpenSpec), so ignore it and pass the spec path explicitly.
4. Findings are a report: posting them as PR comments or requesting changes needs explicit user approval.

Name clash: Claude Code also ships a built-in `/code-review` command (bug-hunting review of the current diff). When asking for this skill, name it explicitly ("la skill code-review del proyecto", via the Skill tool) to get the two-axis Standards/Spec review.

`vitest` (antfu/skills, pinned in `skills-lock.json`, installed 2026-11-09) is the test-framework skill for the frontend (C-14 onward, strict TDD). It documents Vitest 5.1.0-beta.1 (a pre-release): check the installed version before relying on v5-only behavior. It does not cover React Testing Library or React Router (use Context7).

`skill-creator` (anthropics/skills, pinned in `skills-lock.json`) is also installed in `.agents/skills/`; it is an authoring tool, not a coding skill, so it is excluded from the table.

MCP servers are integrations, not skills, and are not registered here: see `docs/skills-mcp/mcp.md` (Context7, configured in `.mcp.json`).

(The `openspec-*` skills also live in `.agents/skills/` but are workflow skills, not coding skills, so they are excluded from this table, as are the global foundation skills: active-orchestrator, kb-creator, roadmap-generator, find-skill, agent-instruction, discovery-research, web-scraper.)

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### tdd
- Red before green: write the failing test first, then only enough code to pass; no speculative features.
- Vertical slices: one test -> one implementation -> repeat. Never write all tests first.
- Test behavior through public interfaces (seams), never internals/private methods; tests must survive refactors.
- Agree the seams under test with the user BEFORE writing tests; no tests at unconfirmed seams.
- No tautological tests: expected values come from an independent source (literal, spec scenario), not recomputed like the code.
- No implementation-coupled tests (mocking internal collaborators, verifying via DB side channel instead of the interface).
- Refactoring is not part of the loop; it belongs to review. (Project strict TDD mode still requires safety net + triangulation.)

### python-testing-patterns
- AAA structure (Arrange/Act/Assert); tests independent, no shared state, clean up after themselves.
- Layout: tests/conftest.py (shared fixtures), test_unit/, test_integration/, test_e2e/.
- Naming: test_<unit>_<scenario>_<expected>; descriptive, no vague names like test_1.
- Use pytest fixtures + parametrize for triangulation; markers (slow, integration) run via `pytest -m`.
- Mock only external boundaries; freeze time with freezegun for time-dependent logic (relevant: turnos, UTC).
- Coverage: meaningful over high %; `pytest --cov --cov-report=term-missing --cov-fail-under=N`.

### fastapi-python
- Functional style; `def` for pure functions, `async def` for I/O; type hints on all signatures; Pydantic v2 models over raw dicts.
- RORO pattern (receive/return an object); explicit router exports; snake_case file names (routers/user_routes.py).
- Guard clauses and early returns; happy path last; avoid else; handle edge cases at function entry.
- HTTPException for expected errors with specific HTTP status; declare return type/response_model on routes.
- Use FastAPI dependency injection (Depends) for DB session, auth, current user.
- Lifespan context managers for startup/shutdown (not on_event); middleware for logging/error monitoring.
- No blocking I/O in async routes; cache with Redis where useful. SQLAlchemy 2.0 style.

### supabase-postgres-best-practices
- Applies to any Postgres schema/migration/SQL work (not Supabase-specific). Read references/<rule>.md for detail (path: .agents/skills/supabase-postgres-best-practices/references/).
- Priority: query perf (query-*), connection mgmt (conn-*), security/RLS (security-*), schema design (schema-*), locking (lock-*), data access (data-*).
- Schema: schema-constraints, schema-primary-keys, schema-data-types, schema-foreign-key-indexes (index every FK), lowercase identifiers.
- Integrity belongs in DB constraints (relevant: no-overlap guarantees via exclusion constraints / btree_gist + tstzrange, CHECK constraints).
- Indexes: composite, partial, covering; verify with EXPLAIN ANALYZE (monitor-explain-analyze).
- Concurrency: keep transactions short, prevent deadlocks (consistent lock order), advisory locks, SKIP LOCKED for queues.
- Data access: avoid N+1, batch inserts, paginate (keyset), upsert via ON CONFLICT.
- Connections: use pooling, set limits/idle timeouts. Least privilege roles (security-privileges).

### auth-implementation-patterns
- Hash passwords with bcrypt/argon2; never store plaintext.
- Short-lived access tokens (15-30 min) with expiry; refresh-token rotation; rotate secrets regularly.
- Authorize server-side on every endpoint (RBAC by role); never trust client data or client-side checks only.
- Avoid JWT in localStorage (XSS); prefer httpOnly + secure + sameSite cookies when feasible.
- Rate-limit auth endpoints; log security events (logins, failed auth); validate all input.
- Secure password reset: expiring single-use tokens. HTTPS everywhere. CSRF protection for cookie/session auth.
- Secrets only from env vars, never in repo.

### revisar-escenarios
- Report only: never edit specs; corrections go back through `/opsx:update` or Propose (hard rule: Apply implements only the approved spec).
- Inputs: change name; reads its delta specs, proposal/design/tasks, its `CHANGES.md` block, the KB "Leer antes" files plus 05, 09, 10.
- Build the applicable rule list (RN/DD/SU) first; every BLOQUEANTE/MAYOR finding must cite a source, otherwise it is a SUGERENCIA.
- Controls C1-C9 (`references/controles.md`): min. expected + business-error + edge scenario; KB traceability; change scope; HTTP contract (409/422/404, 401 vs 403; source: 05 §Excepciones globales); verifiability; time/UTC/fixed clock; ambiguity; hard rules; tasks per scenario.
- Never invent domain rules: missing decisions become open questions for `10_preguntas_abiertas.md`.
- Output: `openspec/changes/<change>/revision-escenarios.md` (append a new "Revisión N" section if it exists) + chat summary with verdict and BLOQUEANTE findings.

### revisar-migraciones
- Report only: never renumber or commit; the change owner fixes it on their branch (team rule: whoever merges second renumbers).
- Run `python .agents/skills/revisar-migraciones/scripts/revisar_migraciones.py` from repo root (`--rama <name>` to scope, `--sin-fetch` offline); exit 0 ok, 1 something to fix, 2 usage/git error. Only sees pushed branches: push first.
- New migration must be `head(main)+1` with `down_revision = head(main)`, or follow another new migration of the same branch; number already in main → RENUMERAR (and every new migration stacked on it); gaps/wrong down_revision → CADENA ROTA; same filename as main with different content → MODIFICA MAIN (never edit merged migrations).
- Integrity: duplicate revision in a branch, multiple heads, unparseable/non-numeric/merge migrations are all problems.
- Same revision added by two open branches = informational clash (does not change exit code): warn both owners (see `Responsable` in `CHANGES.md`).
- After renumbering: `alembic heads` must show a single head; rerun the skill.

### code-review
- Fixed point for a PR is `origin/main`; diff with three dots (`git diff origin/main...HEAD`) so it compares against the merge-base. Verify the ref resolves and the diff is non-empty before spawning sub-agents.
- Two axes, two fresh parallel sub-agents, never merged or reranked: report under `## Standards` and `## Spec`, ending with findings count and worst issue per axis.
- Standards sources in this repo: `CLAUDE.md`/`AGENTS.md` (hard rules: tz-aware datetimes in UTC, exclusion constraints + concurrency test, no SQLite/mocked DB in persistence tests, type hints, Conventional Commits, no real patient data, no secrets), `openspec/config.yaml`, `knowledge-base/08_arquitectura_propuesta.md`. Skip what `ruff format`/`ruff check` already enforce.
- Fowler smell baseline (Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest) is always a judgement call; a documented repo rule overrides it.
- Spec source is the change's OpenSpec folder (active or `archive/<fecha>-<change>/`) plus its `CHANGES.md` block; no issue tracker. Spec axis reports missing/partial requirements, scope creep (hard rule: Apply implements only the approved spec) and wrong implementations, quoting the spec line.
- Report only: never edit code or post to the PR without explicit user approval.

### vitest
- Documents Vitest v5 (5.1.0-beta.1); v5 needs Vite >= 6.4.0 and Node >= 22.12.0. Confirm the installed version first; stable v4 differs in the defaults below.
- React tests: `test.environment: 'jsdom'` (`npm i -D jsdom`) in `vitest.config.ts`, or per file with `// @vitest-environment jsdom` on top. Needs `@vitejs/plugin-react` in the Vite plugins. React Testing Library is NOT covered here.
- Imports are explicit (`import { test, expect, vi } from 'vitest'`) unless `globals: true`.
- Mocks: `vi.fn()`, `vi.spyOn(obj, 'm')`, `vi.mock('./mod', factory)` is hoisted and MUST be top-level (nested calls throw in v5); use `vi.hoisted()` for variables used in factories; `vi.doMock` for dynamic, non-hoisted.
- v5 `clearMocks` defaults to `true` (call history cleared before each test); `vi.restoreAllMocks()` only restores `vi.spyOn` spies.
- Fake timers: `vi.useFakeTimers()`, `vi.advanceTimersByTime(ms)`, `vi.advanceTimersByTimeAsync(ms)` for async callbacks, `vi.setSystemTime(date)`; always `vi.useRealTimers()` in `afterEach`.
- Globals/env: `vi.stubGlobal('fetch', vi.fn())` + `vi.unstubAllGlobals()`; `vi.stubEnv(...)` + `vi.unstubAllEnvs()`. Test values only, never real secrets.
- Hooks: `beforeEach`/`afterEach` for per-test setup/cleanup; `setupFiles` for global setup (e.g. cleanup, matchers).
- Always `await` async assertions (`resolves`, `rejects`): in v5 unawaited ones fail the test. `expect.poll` rejects on timeout in v5.
- `test.sequential`/`describe.sequential` were removed in v5: use `{ concurrent: false }`. Default pool is `forks`; config is not looked up from parent dirs (pass `--config`).
- Experimental/beta (avoid): `--since-last-run`, `experimental.*`, `vi.when`, `bench`.
- Run once (CI/agents): `vitest run` (watch mode is the default in dev).

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| CLAUDE.md / AGENTS.md | CLAUDE.md, AGENTS.md | Project instructions for agents (identical copies): stack, KB map, skills per role, hard rules |
| Project skills | .agents/skills/ | Installed skills (domain + openspec-*); lockfile `skills-lock.json` |
| Knowledge base | knowledge-base/README.md | Index of 10 canonical KB files (01_vision ... 10_preguntas_abiertas) |
| Business rules | knowledge-base/05_reglas_de_negocio.md | RN1-RN6 (no overlaps, [inicio,fin) intervals) |
| Data model | knowledge-base/04_modelo_de_datos.md | |
| Architecture | knowledge-base/08_arquitectura_propuesta.md | |
| Decisions | knowledge-base/09_decisiones_y_supuestos.md | |
| Roadmap | CHANGES.md | 16 MVP changes (C-01..C-16) |
| OpenSpec config | openspec/config.yaml | schema spec-driven; artifacts in es, structural headings/SHALL/MUST in English |

Read the convention files listed above for project-specific patterns and rules.
