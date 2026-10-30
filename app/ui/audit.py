"""Audit log for the Auditor: read-only, plus the chain check (verify_chain in the service
layer)."""

import flet as ft

from app.ui.common import Ctx, call, screen, scroll_body, show_table, toast

COLUMNS = [
    ("id", "#"),
    ("stamp", "When (UTC)"),
    ("actor_id", "Who"),
    ("action", "What"),
    ("target", "On"),
    ("outcome", "Outcome"),
]


def audit_view(ctx: Ctx) -> ft.Control:
    """Newest entries first. There is no edit or delete here, and none in the service layer."""
    body = scroll_body()
    result = ft.Text("")

    def load() -> None:
        """Fetch the entries and redraw the table."""
        show_table(
            ctx,
            body,
            lambda: call(ctx, ctx.svc.list_audit, ctx.token),
            [label for _, label in COLUMNS],
            lambda e: [ft.Text(str(e.get(k, ""))) for k, _ in COLUMNS],
        )

    def verify(e=None) -> None:
        """Run the chain check and show whether any entry was changed or removed."""
        ok, answer = call(ctx, ctx.svc.verify_audit, ctx.token)
        if not ok:
            return
        intact, bad_id = answer
        if intact:
            result.value, result.color = "Chain intact.", ft.Colors.GREEN_300
        else:
            result.value, result.color = f"Tampering at entry #{bad_id}.", ft.Colors.RED_300
        toast(ctx.page, result.value)
        ctx.page.update()

    load()
    return screen(
        "Audit log",
        body,
        ft.Row(
            [result, ft.FilledButton("Verify chain", icon=ft.Icons.VERIFIED_USER, on_click=verify)]
        ),
    )
