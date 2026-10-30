"""UI PREVIEW ONLY: an in-memory stand-in for app/services.py so the screens can be built and
demonstrated before the real backend exists. It is NOT the security implementation and is never
used by the real app (python -m app.main). The real app/services.py, written by the backend
member, must offer these same functions with these same meanings:

    login(username, password) -> token                raises AuthError (one generic message)
    logout(token)
    whoami(token) -> {"id", "username", "roles"}       raises AuthError if expired or deactivated
    can(token, permission) -> bool                     for hiding buttons only, never the control
    list_users(token) / list_roles(token)
    create_user(token, username, password, role)
    set_user_active(token, user_id, active, confirm_password)
    set_user_role(token, user_id, role, grant, confirm_password)
    reset_password(token, user_id, new_password, confirm_password)
    list_records(token, kind) -> list of dicts         kind: "members", "payments" or "plans"
    create_record(token, kind, fields) / update_record(token, kind, record_id, fields)
    delete_record(token, kind, record_id)
    approve_refund(token, payment_id)
    list_audit(token) -> list of dicts / verify_audit(token) -> (ok, first_bad_id)

Errors the screens expect: AuthError (back to login), PermissionDenied (short refusal) and
ValueError (a short validation message that is safe to show).
"""

import itertools


class AuthError(Exception):
    """Not signed in, session expired, or the account is inactive."""


class PermissionDenied(Exception):
    """The signed-in user may not do this."""


# A rough copy of the draft matrix, only so the preview hides and refuses the right things.
_PREVIEW_ROLES = {
    "Administrator": {"user:manage", "role:assign", "member:read", "payment:read", "plan:read"},
    "Front Desk": {
        "member:create",
        "member:read",
        "member:update",
        "payment:create",
        "payment:read",
    },
    "Coach": {
        "member:read",
        "member:read_sensitive",
        "plan:create",
        "plan:read",
        "plan:update",
        "plan:delete",
    },
    "Member": {"plan:read", "payment:read"},
    "Auditor": {"audit:read", "member:read", "payment:read", "plan:read"},
}


class FakeServices:
    """Same calls as the real service layer, with preview data held in memory."""

    AuthError = AuthError
    PermissionDenied = PermissionDenied

    def __init__(self):
        self._ids = itertools.count(100)
        self._users = {
            1: {"id": 1, "username": "admin.ana", "roles": ["Administrator"], "active": True},
            2: {"id": 2, "username": "desk.ben", "roles": ["Front Desk"], "active": True},
            3: {"id": 3, "username": "coach.cris", "roles": ["Coach"], "active": True},
            4: {"id": 4, "username": "member.dana", "roles": ["Member"], "active": True},
            5: {"id": 5, "username": "audit.eli", "roles": ["Auditor"], "active": True},
        }
        self._records = {
            "members": [
                {
                    "id": 1,
                    "full_name": "Dana Reyes",
                    "contact_number": "0917-***-**21",
                    "health_notes": "•••••",
                    "membership_type": "Monthly",
                }
            ],
            "payments": [
                {
                    "id": 1,
                    "member_id": 1,
                    "amount": "1500.00",
                    "kind": "payment",
                    "status": "recorded",
                },
                {
                    "id": 2,
                    "member_id": 1,
                    "amount": "500.00",
                    "kind": "refund",
                    "status": "pending",
                },
            ],
            "plans": [
                {"id": 1, "member_id": 1, "title": "Beginner strength", "details": "3x a week"}
            ],
        }
        self._audit = []
        self._sessions = {}

    # -- sessions ---------------------------------------------------------------------------
    def login(self, username, password):
        """Sign in with any non-empty password (preview only)."""
        user = next((u for u in self._users.values() if u["username"] == username), None)
        if user is None or not user["active"] or not password:
            self._log(None, "LOGIN", username, "FAIL")
            raise AuthError("Invalid username or password.")
        token = f"preview-{next(self._ids)}"
        self._sessions[token] = user["id"]
        self._log(user["id"], "LOGIN", username, "OK")
        return token

    def logout(self, token):
        """End the preview session."""
        self._sessions.pop(token, None)

    def whoami(self, token):
        """The signed-in user, or AuthError if the session is gone or the user is inactive."""
        user = self._users.get(self._sessions.get(token))
        if user is None or not user["active"]:
            raise AuthError("Please sign in again.")
        return dict(user)

    def can(self, token, permission):
        """Whether the preview matrix grants this permission."""
        user = self._users.get(self._sessions.get(token))
        return bool(
            user and user["active"] and any(permission in _PREVIEW_ROLES[r] for r in user["roles"])
        )

    def _need(self, token, permission):
        self.whoami(token)  # an unknown, expired or deactivated session ends here (AuthError)
        if not self.can(token, permission):
            self._log(self._sessions.get(token), "DENY", permission, "FAIL")
            raise PermissionDenied(permission)

    # -- users ------------------------------------------------------------------------------
    def list_users(self, token):
        """All preview users."""
        self._need(token, "user:manage")
        return [dict(u) for u in self._users.values()]

    def list_roles(self, token):
        """The five preview roles."""
        return list(_PREVIEW_ROLES)

    def create_user(self, token, username, password, role):
        """Add a preview user (rejects short passwords like the real service)."""
        self._need(token, "user:manage")
        if len(password) < 12:
            raise ValueError("Password must be 12 characters or more.")
        uid = next(self._ids)
        self._users[uid] = {"id": uid, "username": username, "roles": [role], "active": True}
        self._log(self._sessions[token], "CREATE", f"user:{uid}", "OK")
        return uid

    def set_user_active(self, token, user_id, active, confirm_password):
        """Deactivate or reactivate a preview user."""
        self._need(token, "user:manage")
        self._users[user_id]["active"] = active
        self._log(
            self._sessions[token], "ACTIVATE" if active else "DEACTIVATE", f"user:{user_id}", "OK"
        )

    def set_user_role(self, token, user_id, role, grant, confirm_password):
        """Grant or revoke a role; refuses changes to your own roles."""
        self._need(token, "role:assign")
        if user_id == self._sessions[token]:
            raise ValueError("You can't change your own roles.")
        roles = self._users[user_id]["roles"]
        if grant and role not in roles:
            roles.append(role)
        elif not grant and role in roles:
            roles.remove(role)
        self._log(
            self._sessions[token], "GRANT" if grant else "REVOKE", f"user:{user_id}:{role}", "OK"
        )

    def reset_password(self, token, user_id, new_password, confirm_password):
        """Pretend to reset a password (rejects short ones)."""
        self._need(token, "user:manage")
        if len(new_password) < 12:
            raise ValueError("Password must be 12 characters or more.")
        self._log(self._sessions[token], "RESET_PASSWORD", f"user:{user_id}", "OK")

    # -- records ----------------------------------------------------------------------------
    _PERM = {"members": "member", "payments": "payment", "plans": "plan"}

    def list_records(self, token, kind):
        """The preview records of one kind."""
        self._need(token, f"{self._PERM[kind]}:read")
        return [dict(r) for r in self._records[kind]]

    def create_record(self, token, kind, fields):
        """Add a preview record."""
        self._need(token, f"{self._PERM[kind]}:create")
        rid = next(self._ids)
        self._records[kind].append({"id": rid, **fields})
        self._log(self._sessions[token], "CREATE", f"{kind}:{rid}", "OK")

    def update_record(self, token, kind, record_id, fields):
        """Change a preview record."""
        self._need(token, f"{self._PERM[kind]}:update")
        next(r for r in self._records[kind] if r["id"] == record_id).update(fields)
        self._log(self._sessions[token], "UPDATE", f"{kind}:{record_id}", "OK")

    def delete_record(self, token, kind, record_id):
        """Remove a preview record."""
        self._need(token, f"{self._PERM[kind]}:delete")
        self._records[kind] = [r for r in self._records[kind] if r["id"] != record_id]
        self._log(self._sessions[token], "DELETE", f"{kind}:{record_id}", "OK")

    def approve_refund(self, token, payment_id):
        """Refuse unless the preview matrix allows it."""
        self._need(token, "payment:approve_refund")

    # -- audit ------------------------------------------------------------------------------
    def list_audit(self, token):
        """Preview audit entries, newest first."""
        self._need(token, "audit:read")
        return list(reversed(self._audit))

    def verify_audit(self, token):
        """The preview chain is always intact."""
        self._need(token, "audit:read")
        return True, None

    def _log(self, actor_id, action, target, outcome):
        self._audit.append(
            {
                "id": len(self._audit) + 1,
                "stamp": "preview",
                "actor_id": actor_id,
                "action": action,
                "target": target,
                "outcome": outcome,
            }
        )
