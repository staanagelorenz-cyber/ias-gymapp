# IAS Gym App Backend Steps for Groupmate

This guide coordinates the real backend used by the Flet screens. The UI is already in `app/ui/`. The RBAC teammate owns `app/rbac.py` and its `require()` authorization function. The backend implementer owns `app/services.py`, `app/auth.py`, `app/audit.py`, and `app/crypto.py`; service operations call `require()` to enforce authorization. The in-memory module in `tests/fake_services.py` is only a UI preview and must not be used by the real app.

## 1. Set up the database

Use SQLite for the current schema. Create the database from the repository root:

```sh
mkdir -p data
sqlite3 data/gymapp.db < data/schema.sql
```

Enable foreign keys on every SQLite connection (`PRAGMA foreign_keys = ON`). The schema creates `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `members`, `payments`, `plans`, and `audit_log`. It seeds the roles, permissions, and initial role grants. `members.user_id` links a gym member to their login account and may be `NULL` for members without an account. Do not store plaintext passwords; `users.password_hash` must contain a password hash produced by `app/crypto.py`.

Keep the database file and any secrets out of version control. Commit the schema, not a populated database.

## 2. RBAC teammate: implement `app/rbac.py`

Implement role and permission setup and checks using the join tables. Seed these role names exactly:

- Administrator
- Front Desk
- Coach
- Member
- Auditor

Seed the permissions below exactly as written; the UI and backend must use the same strings:

```text
user:manage
role:assign
member:create
member:read
member:update
member:delete
member:read_sensitive
payment:create
payment:read
payment:approve_refund
plan:create
plan:read
plan:update
plan:update_any
plan:delete
audit:read
```

The schema seeds these initial role grants:

| Role | Permissions |
| --- | --- |
| Administrator | `user:manage`, `role:assign`, `member:read`, `payment:approve_refund` |
| Front Desk | `member:create`, `member:read`, `member:update`, `payment:create`, `payment:read` |
| Coach | `member:read`, `member:read_sensitive`, `plan:create`, `plan:read`, `plan:update`, `plan:delete` |
| Member | `plan:read`, `payment:read` |
| Auditor | `member:read`, `payment:read`, `plan:read`, `audit:read` |

`app/rbac.py` owns the `require()` function that checks whether an authenticated actor has the requested permission, and should also expose whatever session/identity helpers the service layer needs. The service layer must invoke it on every protected operation; UI button visibility through `can()` is not an authorization boundary. Restrict a Coach's plan edits to plans where `owner_id` is their user ID; `plan:update_any` permits broader editing. A Member's account maps through `members.user_id`; scope that member's plan and payment queries to their own linked member record. Administrator intentionally lacks `audit:read` and broad data-edit permissions; refund approval remains Administrator-only under the current grants. The role-to-permission mapping is persisted in `role_permissions`, not merely held in Python constants.

## 3. Backend implementer: `app/services.py`, `app/auth.py`, `app/audit.py`, `app/crypto.py`

The screens import a service object with this interface (see `tests/fake_services.py` for the preview shape):

```text
login(username, password) -> token
logout(token)
whoami(token) -> {"id", "username", "roles"}
can(token, permission) -> bool
list_users(token) / list_roles(token)
create_user(token, username, password, role)
set_user_active(token, user_id, active, confirm_password)
set_user_role(token, user_id, role, grant, confirm_password)
reset_password(token, user_id, new_password, confirm_password)
list_records(token, kind) -> list of dictionaries
create_record(token, kind, fields) / update_record(token, kind, record_id, fields)
delete_record(token, kind, record_id)
approve_refund(token, payment_id)
list_audit(token) -> list of dictionaries
verify_audit(token) -> (intact, first_bad_id)
```

`kind` is `members`, `payments`, or `plans`. Return record dictionaries using the fields shown in `app/ui/records.py`; sensitive member fields should be masked unless the caller has `member:read_sensitive`. Audit rows should include `id`, `stamp`, `actor_id`, `action`, `target`, and `outcome`.

Raise `AuthError` for invalid, expired, or deactivated sessions; `PermissionDenied` for forbidden actions; and `ValueError` only for safe-to-display validation messages. Unexpected database or implementation errors should not expose SQL, stack traces, password data, or internal details to the UI.

## 4. Apply security rules in the service layer

- Use parameterized SQL for every query.
- Use a password hashing library to store and verify password hashes. Require at least 12 characters for new or reset passwords, matching the UI.
- Return the same login error for unknown usernames, wrong passwords, inactive accounts, and locked accounts. Track failed attempts in `failed` and enforce the `locked_until` policy consistently.
- Check the session and permission on every protected service call. Deactivating an account must invalidate its active sessions.
- Require the caller's current password for account deactivation/reactivation, role changes, and password resets. Do not allow users to change their own roles; protect against removing or deactivating the last Administrator.
- A refund is recorded as `kind='refund'` with `status='pending'`. Only a user with `payment:approve_refund` may approve it, and the person who recorded it must not approve their own refund.
- Write audit entries for authentication outcomes, permission denials, user/role changes, sensitive reads or changes, payment/refund actions, and plan/member changes. Never include passwords, password hashes, or unnecessary health/contact data in audit details.
- Keep audit records append-only through the application interface. `audit_log.prev_hash` and `audit_log.entry_hash` are provided for the HMAC chain (Pattern 3); `app/crypto.py` should generate/verify HMACs and `app/audit.py` should append and verify entries in order. Define a stable canonical representation of each entry and include the previous hash in the authenticated payload. Keep the HMAC key outside the database and source control.

## 5. Connect and run the app

`app/main.py` imports `app.services` when launching the real application. Implement the module so this works:

```sh
python -m app.main
```

The preview remains separate:

```sh
python -m tests.preview
```

Do not make production startup silently fall back to `tests.fake_services`.

## 6. Coordinate the contract

Keep `users.failed`, `users.locked_until`, `members.user_id`, `payments.recorded_by`, `payments.status`, `plans.owner_id`, and the audit hash fields aligned with `data/schema.sql`. Coordinate any schema changes with its owner. Sessions may be held in memory for the initial implementation; if persistent session storage is introduced, update the schema and this guide together.
