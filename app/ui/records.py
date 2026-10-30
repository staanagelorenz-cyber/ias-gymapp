"""One screen for the three protected resources: members, payments and training plans.

Buttons are shown only when svc.can() says so. That is a convenience: the service layer checks the
same permission again on every call, so a hidden button is never the thing that protects data.
"""
import flet as ft

from app.ui.common import Ctx, call, close, form_dialog

# kind -> what the screen shows. "sensitive" fields arrive already masked from the service, so on
# edit they start empty and are only sent when the user types a new value.
KINDS = {
    "members": {
        "title": "Members", "perm": "member",
        "columns": [("full_name", "Name"), ("contact_number", "Contact"), ("health_notes", "Health notes"),
                    ("membership_type", "Membership")],
        "sensitive": {"contact_number", "health_notes"},
    },
    "payments": {
        "title": "Payments", "perm": "payment",
        "columns": [("member_id", "Member #"), ("amount", "Amount (PHP)"), ("kind", "Type"), ("status", "Status")],
        "read_only": {"status"},  # the service sets status; refunds are approved by someone else
        "choices": {"kind": ["payment", "refund"]},
        "sensitive": set(),
    },
    "plans": {
        "title": "Training plans", "perm": "plan",
        "columns": [("member_id", "Member #"), ("title", "Title"), ("details", "Details")],
        "sensitive": set(),
    },
}


def records_view(ctx: Ctx, kind: str) -> ft.Control:
    """The list for one kind of record, with add, edit and delete where the user may."""
    spec = KINDS[kind]
    can = {action: ctx.svc.can(ctx.token, f"{spec['perm']}:{action}") for action in ("create", "update", "delete")}
    can_approve = kind == "payments" and ctx.svc.can(ctx.token, "payment:approve_refund")
    body = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)

    def load():
        rows = call(ctx, ctx.svc.list_records, ctx.token, kind)
        body.controls = [table(rows)] if rows not in (None, True) else [ft.Text("Nothing to show.")]
        ctx.page.update()

    def table(rows):
        columns = [ft.DataColumn(ft.Text(label)) for _, label in spec["columns"]] + [ft.DataColumn(ft.Text(""))]
        return ft.DataTable(columns=columns, rows=[
            ft.DataRow(cells=[ft.DataCell(ft.Text(str(r.get(key, "")))) for key, _ in spec["columns"]]
                       + [ft.DataCell(actions(r))])
            for r in rows])

    def actions(record):
        buttons = []
        if can["update"]:
            buttons.append(ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e: editor(record)))
        if can["delete"]:
            buttons.append(ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Delete", on_click=lambda e: delete(record)))
        if can_approve and record.get("kind") == "refund" and record.get("status") == "pending":
            buttons.append(ft.TextButton("Approve refund", on_click=lambda e: approve(record)))
        return ft.Row(buttons, spacing=0)

    def editor(record=None):
        inputs = {}
        for key, label in spec["columns"]:
            if key in spec.get("read_only", set()):
                continue
            if key in spec.get("choices", {}):
                inputs[key] = ft.Dropdown(label=label, value=(record or {}).get(key),
                                          options=[ft.DropdownOption(c, c) for c in spec["choices"][key]])
            else:
                start = "" if record is None or key in spec["sensitive"] else str(record.get(key, ""))
                hint = "Leave empty to keep the current value" if record and key in spec["sensitive"] else None
                inputs[key] = ft.TextField(label=label, value=start, hint_text=hint)

        def save():
            fields = {k: (c.value or "").strip() for k, c in inputs.items()}
            if record is not None:  # don't overwrite a hidden value with an empty one
                fields = {k: v for k, v in fields.items() if v or k not in spec["sensitive"]}
            close(ctx.page)
            if record is None:
                ok = call(ctx, ctx.svc.create_record, ctx.token, kind, fields, done="Saved.")
            else:
                ok = call(ctx, ctx.svc.update_record, ctx.token, kind, record["id"], fields, done="Saved.")
            if ok:
                load()
        form_dialog(ctx.page, f"{'Edit' if record else 'Add'} {spec['title'].lower().rstrip('s')}",
                    list(inputs.values()), save)

    def delete(record):
        def go():
            close(ctx.page)
            if call(ctx, ctx.svc.delete_record, ctx.token, kind, record["id"], done="Deleted."):
                load()
        form_dialog(ctx.page, "Delete this record?", [ft.Text("This can't be undone.")], go, save_text="Delete")

    def approve(record):
        if call(ctx, ctx.svc.approve_refund, ctx.token, record["id"], done="Refund approved."):
            load()

    load()
    add = [ft.FilledButton(f"Add {spec['title'].lower().rstrip('s')}", icon=ft.Icons.ADD,
                           on_click=lambda e: editor())] if can["create"] else []
    return ft.Column([ft.Row([ft.Text(spec["title"], size=22, weight=ft.FontWeight.BOLD), *add],
                             alignment=ft.MainAxisAlignment.SPACE_BETWEEN), body], expand=True)
