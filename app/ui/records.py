"""One screen for the three protected resources: members, payments and training plans.

Buttons are shown only when the service says the user may use them. That is a convenience: the
service layer checks the same permission again on every call, so a hidden button is never the
thing that protects data.
"""

import flet as ft

from app.ui.common import (
    Ctx,
    call,
    can,
    dropdown,
    form_dialog,
    screen,
    scroll_body,
    show_table,
)

# kind -> what the screen shows. "sensitive" fields arrive already masked from the service, so
# on edit they start empty and are only sent when the user types a new value.
KINDS = {
    "members": {
        "title": "Members",
        "one": "member",
        "perm": "member",
        "columns": [
            ("full_name", "Name"),
            ("contact_number", "Contact"),
            ("health_notes", "Health notes"),
            ("membership_type", "Membership"),
        ],
        "sensitive": {"contact_number", "health_notes"},
    },
    "payments": {
        "title": "Payments",
        "one": "payment",
        "perm": "payment",
        "columns": [
            ("member_id", "Member #"),
            ("amount", "Amount (PHP)"),
            ("kind", "Type"),
            ("status", "Status"),
        ],
        "read_only": {"status"},  # the service sets status; refunds are approved by someone else
        "choices": {"kind": ["payment", "refund"]},
        "sensitive": set(),
    },
    "plans": {
        "title": "Training plans",
        "one": "plan",
        "perm": "plan",
        "columns": [("member_id", "Member #"), ("title", "Title"), ("details", "Details")],
        "sensitive": set(),
    },
}


def records_view(ctx: Ctx, kind: str) -> ft.Control:
    """The list for one kind of record, with add, edit and delete where the user may."""
    spec = KINDS[kind]
    allowed = {a: can(ctx, f"{spec['perm']}:{a}") for a in ("create", "update", "delete")}
    can_approve = kind == "payments" and can(ctx, "payment:approve_refund")
    body = scroll_body()

    def load() -> None:
        """Fetch the records again and redraw the table."""
        show_table(
            ctx,
            body,
            lambda: call(ctx, ctx.svc.list_records, ctx.token, kind),
            [label for _, label in spec["columns"]] + [""],
            lambda r: [ft.Text(str(r.get(k, ""))) for k, _ in spec["columns"]] + [actions(r)],
        )

    def actions(record: dict) -> ft.Control:
        """The buttons on one row, only those the user may use."""
        buttons = []
        if allowed["update"]:
            buttons.append(
                ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e: editor(record))
            )
        if allowed["delete"]:
            buttons.append(
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE, tooltip="Delete", on_click=lambda e: delete(record)
                )
            )
        if can_approve and record.get("kind") == "refund" and record.get("status") == "pending":
            buttons.append(ft.TextButton("Approve refund", on_click=lambda e: approve(record)))
        return ft.Row(buttons, spacing=0)

    def editor(record: dict | None = None) -> None:
        """Add a new record (record is None) or edit one."""
        inputs = {}
        for key, label in spec["columns"]:
            if key in spec.get("read_only", set()):
                continue
            current = (record or {}).get(key)
            if key in spec.get("choices", {}):
                inputs[key] = dropdown(label, spec["choices"][key], current)
            elif record is not None and key in spec["sensitive"]:
                inputs[key] = ft.TextField(
                    label=label, hint_text="Leave empty to keep the current value"
                )
            else:
                inputs[key] = ft.TextField(
                    label=label, value="" if current is None else str(current)
                )

        def save() -> bool:
            """Send the fields; keep the dialog open if the service refuses them."""
            fields = {k: (c.value or "").strip() for k, c in inputs.items()}
            if record is None:
                ok, _ = call(ctx, ctx.svc.create_record, ctx.token, kind, fields, done="Saved.")
            else:  # an empty sensitive field means "unchanged": don't overwrite it with nothing
                fields = {k: v for k, v in fields.items() if v or k not in spec["sensitive"]}
                ok, _ = call(
                    ctx,
                    ctx.svc.update_record,
                    ctx.token,
                    kind,
                    record["id"],
                    fields,
                    done="Saved.",
                )
            if ok:
                load()
            return ok

        form_dialog(
            ctx.page, f"{'Edit' if record else 'Add'} {spec['one']}", list(inputs.values()), save
        )

    def delete(record: dict) -> None:
        """Ask first, then delete."""

        def go() -> bool:
            """Delete after the user confirmed."""
            ok, _ = call(
                ctx, ctx.svc.delete_record, ctx.token, kind, record["id"], done="Deleted."
            )
            if ok:
                load()
            return True  # close either way: the message says what happened

        form_dialog(
            ctx.page,
            "Delete this record?",
            [ft.Text("This can't be undone.")],
            go,
            save_text="Delete",
        )

    def approve(record: dict) -> None:
        """Approve a pending refund (the service refuses if you recorded it yourself)."""
        ok, _ = call(ctx, ctx.svc.approve_refund, ctx.token, record["id"], done="Refund approved.")
        if ok:
            load()

    load()
    add = (
        [ft.FilledButton(f"Add {spec['one']}", icon=ft.Icons.ADD, on_click=lambda e: editor())]
        if allowed["create"]
        else []
    )
    return screen(spec["title"], body, *add)
