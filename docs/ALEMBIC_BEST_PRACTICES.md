# Alembic Best Practices (Quality Checklist)

Use this checklist when creating or reviewing migrations. It focuses on safety
and avoids disruptive operations in production environments.

- Prefer concurrent index creation in PostgreSQL for large tables.
- Split unique constraints into "create index" + "add constraint" steps when needed.
- Add foreign keys as NOT VALID, then validate separately for safety.
- Avoid changing column types in a single operation; prefer multi-step migrations.
- Limit non-unique indexes to a maximum of three columns.
- Avoid redundant indexes already covered by composite indexes.

These guidelines align with the `sqlalchemy-alembic-expert-best-practices-code-review`
skill rules in `.agents/skills/`.
