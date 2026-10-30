"""User administration: create users, deactivate or reactivate them, grant or revoke roles, and
reset passwords. The safeguards (last administrator, no self-escalation, checking the re-entered
password) live in the service layer; this screen only collects the input and shows the answer."""
import flet as ft

from app.ui.common import Ctx, call, close, confirm_with_password, form_dialog


def users_view(ctx: Ctx) -> ft.Control:
    """The user list with the administrator's actions."""
    roles = call(ctx, ctx.svc.list_roles, ctx.token) or []
    body = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)

    def load():
        users = call(ctx, ctx.svc.list_users, ctx.token)
        if users in (None, True):
            body.controls = [ft.Text("Nothing to show.")]
        else:
            body.controls = [ft.DataTable(
                columns=[ft.DataColumn(ft.Text(t)) for t in ("Username", "Roles", "Status", "")],
                rows=[ft.DataRow(cells=[
                    ft.DataCell(ft.Text(u["username"])),
                    ft.DataCell(ft.Text(", ".join(u["roles"]) or "none")),
                    ft.DataCell(ft.Text("Active" if u["active"] else "Deactivated")),
                    ft.DataCell(actions(u)),
                ]) for u in users])]
        ctx.page.update()

    def actions(user):
        return ft.Row([
            ft.TextButton("Deactivate" if user["active"] else "Reactivate", on_click=lambda e: toggle(user)),
            ft.TextButton("Roles", on_click=lambda e: change_role(user)),
            ft.TextButton("Reset password", on_click=lambda e: reset(user)),
        ], spacing=0)

    def create():
        name = ft.TextField(label="Username")
        password = ft.TextField(label="Temporary password (12+ characters)", password=True, can_reveal_password=True)
        role = ft.Dropdown(label="Role", options=[ft.DropdownOption(r, r) for r in roles])

        def save():
            close(ctx.page)
            if call(ctx, ctx.svc.create_user, ctx.token, (name.value or "").strip(), password.value or "",
                    role.value, done="User created."):
                load()
        form_dialog(ctx.page, "New user", [name, password, role], save, save_text="Create")

    def toggle(user):
        active = not user["active"]
        word = "Reactivate" if active else "Deactivate"

        def go(confirm):
            if call(ctx, ctx.svc.set_user_active, ctx.token, user["id"], active, confirm, done=f"{word}d."):
                load()
        confirm_with_password(ctx.page, f"{word} {user['username']}?",
                              "A deactivated user is signed out at once." if not active else "They can sign in again.",
                              go)

    def change_role(user):
        role = ft.Dropdown(label="Role", options=[ft.DropdownOption(r, r) for r in roles])
        grant = ft.Dropdown(label="Action", value="grant",
                            options=[ft.DropdownOption("grant", "Grant"), ft.DropdownOption("revoke", "Revoke")])

        def next_step():
            close(ctx.page)
            if not role.value:
                return

            def go(confirm):
                if call(ctx, ctx.svc.set_user_role, ctx.token, user["id"], role.value, grant.value == "grant",
                        confirm, done="Roles updated."):
                    load()
            confirm_with_password(ctx.page, "Confirm role change",
                                  f"{grant.value.title()} {role.value} for {user['username']}.", go)
        form_dialog(ctx.page, f"Roles for {user['username']}", [role, grant], next_step, save_text="Next")

    def reset(user):
        new = ft.TextField(label="New temporary password (12+ characters)", password=True, can_reveal_password=True)

        def next_step():
            close(ctx.page)

            def go(confirm):
                call(ctx, ctx.svc.reset_password, ctx.token, user["id"], new.value or "", confirm,
                     done="Password reset.")
            confirm_with_password(ctx.page, "Confirm password reset", f"Reset the password for {user['username']}.", go)
        form_dialog(ctx.page, f"Reset password: {user['username']}", [new], next_step, save_text="Next")

    load()
    return ft.Column([
        ft.Row([ft.Text("Users", size=22, weight=ft.FontWeight.BOLD),
                ft.FilledButton("New user", icon=ft.Icons.PERSON_ADD, on_click=lambda e: create())],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        body], expand=True)
