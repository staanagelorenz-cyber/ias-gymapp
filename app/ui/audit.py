"""Audit log for the Auditor: read-only, plus the chain check (verify_chain in the service layer)."""
import flet as ft

from app.ui.common import Ctx, call, toast

COLUMNS = [("id", "#"), ("stamp", "When (UTC)"), ("actor_id", "Who"), ("action", "What"), ("target", "On"),
           ("outcome", "Outcome")]


def audit_view(ctx: Ctx) -> ft.Control:
    """Newest entries first. There is no edit or delete here, and none in the service layer either."""
    body = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
    result = ft.Text("")

    def load():
        entries = call(ctx, ctx.svc.list_audit, ctx.token)
        if entries in (None, True):
            body.controls = [ft.Text("Nothing to show.")]
        else:
            body.controls = [ft.DataTable(
                columns=[ft.DataColumn(ft.Text(label)) for _, label in COLUMNS],
                rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(str(e.get(k, "")))) for k, _ in COLUMNS])
                      for e in entries])]
        ctx.page.update()

    def verify(e=None):
        answer = call(ctx, ctx.svc.verify_audit, ctx.token)
        if answer in (None, True):
            return
        ok, bad_id = answer
        result.value = "Chain intact: no entry was changed or removed." if ok else \
            f"Tampering detected at entry #{bad_id}."
        result.color = ft.Colors.GREEN_300 if ok else ft.Colors.RED_300
        toast(ctx.page, result.value)
        ctx.page.update()

    load()
    return ft.Column([
        ft.Row([ft.Text("Audit log", size=22, weight=ft.FontWeight.BOLD),
                ft.Row([result, ft.FilledButton("Verify chain", icon=ft.Icons.VERIFIED_USER, on_click=verify)])],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        body], expand=True)
