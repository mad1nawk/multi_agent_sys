# MEMORY — human-readable mirror of long-term memory

<!-- GENERATED from Mem0. Manual edits are allowed and take precedence on the next sync. -->
<!-- One atomic fact per row. English only. No raw dialogue, no secrets. -->

## Schema
`id | topic | fact | date | source | status`
- kind groups the tables below: profile, goal, constraint, knowledge, preference
- status: `active` | `superseded` | `stale` (superseded and stale rows are never retrieved)

## Profile
| id | topic | fact | date | source | status |
|---|---|---|---|---|---|
| P-001 | programme | 2nd-year Software Engineering student | 2026-09-01 | student statement | active |
| P-002 | stack | Works with Python, Flask, SQLAlchemy; Java for coursework | 2026-09-14 | student statement | active |

## Goals
| id | topic | fact | date | source | status |
|---|---|---|---|---|---|
| G-001 | session | Pass the winter exam session with strong grades | 2026-10-02 | student statement | active |
| G-002 | coursework | Deliver a Flask service by 2026-12-01 | 2026-11-03 | student statement | active |

## Constraints
| id | topic | fact | date | source | status |
|---|---|---|---|---|---|
| C-001 | time | <= 3 study hours on weekdays, <= 5 on weekends | 2026-10-02 | student statement | active |
| C-002 | language | All interaction and stored facts in English | 2026-11-16 | student statement | active |

## Knowledge state (time-sensitive)
| id | topic | fact | date | source | status |
|---|---|---|---|---|---|
| K-001 | integration by parts | Sign errors when applying the formula | 2026-11-10 | verified task | active |
| K-002 | integration by parts | Solved two tasks correctly after feedback | 2026-11-15 | verified task | active |
| K-003 | mutex vs semaphore | Conflates ownership with counting | 2026-11-12 | judge verdict | active |
| K-004 | socket lifecycle | Handles client disconnects correctly | 2026-11-14 | verified task | active |

## Preferences
| id | topic | fact | date | source | status |
|---|---|---|---|---|---|
| R-001 | style | Intuition first, then formalism; short runnable examples | 2026-09-20 | student statement | active |
| R-002 | examples | Python by default, Java when the course requires it | 2026-09-20 | student statement | active |

## Maintenance policy
- Knowledge facts older than 90 days without re-confirmation become `stale` and leave retrieval.
- Weekly consolidation: deduplicate near-identical facts, merge same-topic updates,
  mark contradicted rows `superseded`.
- Every memory operation is traced; nothing is rewritten silently.