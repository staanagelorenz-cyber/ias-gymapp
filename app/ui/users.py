"""User administration: create users, deactivate or reactivate them, grant or revoke roles, and
reset passwords. The safeguards (last administrator, no self-escalation, checking the re-entered
password) live in the service layer; this screen only collects the input and shows the answer."""

import flet as ft

from app.ui.common import (
    Ctx,
    call,
    close,
    confirm_with_password,
    dropdown,
    form_dialog,
    screen,
    scroll_body,
    show_table,
    toast,
)


def users_view(ctx: Ctx) -> ft.Control:
    """The user list with the administrator's actions."""
    ok, roles = call(ctx, ctx.svc.list_roles, ctx.token)
    roles = roles if ok else []
    body = scroll_body()

    def load() -> None:
        """Fetch the users again and redraw the table."""
        show_table(
            ctx,
            body,
            lambda: call(ctx, ctx.svc.list_users, ctx.token),
            ["Username", "Roles", "Status", ""],
            lambda u: [
                ft.Text(u["username"]),
                ft.Text(", ".join(u["roles"]) or "none"),
                ft.Text("Active" if u["active"] else "Deactivated"),
                actions(u),
            ],
        )

    def actions(user: dict) -> ft.Control:
        """The administrator's buttons for one user."""
        return ft.Row(
            [
                ft.TextButton(
                    "Deactivate" if user["active"] else "Reactivate",
                    on_click=lambda e: toggle(user),
                ),
                ft.TextButton("Roles", on_click=lambda e: change_role(user)),
                ft.TextButton("Reset password", on_click=lambda e: reset(user)),
            ],
            spacing=0,
        )

    def done(ok: bool) -> bool:
        """After a successful change, reload the list. Returns ok so the dialog knows."""
        if ok:
            load()
        return ok

    def create() -> None:
        """New user with a temporary password and one role."""
        name = ft.TextField(label="Username")
        password = ft.TextField(
            label="Temporary password (12+ characters)", password=True, can_reveal_password=True
        )
        role = dropdown("Role", roles)
        form_dialog(
            ctx.page,
            "New user",
            [name, password, role],
            lambda: done(
                call(
                    ctx,
                    ctx.svc.create_user,
                    ctx.token,
                    (name.value or "").strip(),
                    password.value or "",
                    role.value,
                    done="User created.",
                )[0]
            ),
            save_text="Create",
        )

    def toggle(user: dict) -> None:
        """Deactivate or reactivate, after the administrator re-enters their password."""
        active = not user["active"]
        word = "Reactivate" if active else "Deactivate"
        note = "They can sign in again." if active else "A deactivated user is signed out at once."
        confirm_with_password(
            ctx.page,
            f"{word} {user['username']}?",
            note,
            lambda pw: done(
                call(
                    ctx,
                    ctx.svc.set_user_active,
                    ctx.token,
                    user["id"],
                    active,
                    pw,
                    done=f"{word}d.",
                )[0]
            ),
        )

    def then_confirm(title: str, message: str, action) -> bool:
        """Second step of a two-step change: close the first dialog, ask for the password."""
        close(ctx.page)
        confirm_with_password(ctx.page, title, message, lambda pw: done(action(pw)))
        return False  # the first dialog was closed here already

    def change_role(user: dict) -> None:
        """Grant or revoke one role (the service refuses changes to your own roles)."""
        role = dropdown("Role", roles)
        grant = dropdown("Action", ["Grant", "Revoke"], "Grant")

        def next_step() -> bool:
            """Check a role was chosen, then ask for the password."""
            if not role.value:
                toast(ctx.page, "Choose a role first.")
                return False
            return then_confirm(
                "Confirm role change",
                f"{grant.value} {role.value} for {user['username']}.",
                lambda pw: call(
                    ctx,
                    ctx.svc.set_user_role,
                    ctx.token,
                    user["id"],
                    role.value,
                    grant.value == "Grant",
                    pw,
                    done="Roles updated.",
                )[0],
            )

        form_dialog(
            ctx.page, f"Roles for {user['username']}", [role, grant], next_step, save_text="Next"
        )

    def reset(user: dict) -> None:
        """Set a new temporary password for a user."""
        new = ft.TextField(
            label="New temporary password (12+ characters)",
            password=True,
            can_reveal_password=True,
        )
        form_dialog(
            ctx.page,
            f"Reset password: {user['username']}",
            [new],
            lambda: then_confirm(
                "Confirm password reset",
                f"Reset the password for {user['username']}.",
                lambda pw: call(
                    ctx,
                    ctx.svc.reset_password,
                    ctx.token,
                    user["id"],
                    new.value or "",
                    pw,
                    done="Password reset.",
                )[0],
            ),
            save_text="Next",
        )

    load()
    return screen(
        "Users",
        body,
        ft.FilledButton("New user", icon=ft.Icons.PERSON_ADD, on_click=lambda e: create()),
    )
