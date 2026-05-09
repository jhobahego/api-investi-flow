# Implementation Plan: Quality Improvements (No Feature Changes)

This plan lists quality-focused changes only. Each item should be implemented in a
separate branch starting from `develop`, as described below.

## Branch: chore/implementation-plan (this file only)

- Add this plan document to track quality improvements.

## Branch: chore/settings-hardening

- Introduce cached settings access in `app/core/config.py` using `lru_cache`.
- Use `SecretStr` for secrets and add clear, early validation for required settings.
- Normalize CORS origins and file extension parsing helpers without changing behavior.

## Branch: chore/sqlalchemy-quality

- Update `app/repositories/base.py` to avoid relying on `__dict__` for updates and
  ensure safe, explicit field updates.
- Align repository update patterns with SQLAlchemy best practices.
- Perform a lightweight Alembic safety audit note for index/constraint patterns.

## Branch: chore/pydantic-schemas

- Standardize `model_config = ConfigDict(from_attributes=True)` across response
  schemas.
- Replace manual validators with `Field` constraints where equivalent.

## Branch: chore/api-typing

- Add explicit return types in API endpoints where missing.
- Ensure `response_model` is consistently declared for endpoints.

## Branch: chore/service-patterns

- Apply guard clauses and explicit error handling in services for clarity.
- Reduce duplicated checks in services while keeping behavior identical.

## Branch: chore/testing-improvements

- Add missing error-path tests and parameterized cases.
- Organize tests with consistent markers and fixtures for clarity.

## Branch: docs/background-jobs-audit

- Add documentation identifying candidates for background jobs (long-running or
  IO-heavy flows) without implementing new behavior.
