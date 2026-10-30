"""The screens against the preview stub: each role sees only its sections, a refused call shows a
short message instead of crashing, a rejected form keeps what was typed, and a session that ends
sends the user back to sign-in. These test the interface only; the authorization matrix test
(test_authz_matrix.py) tests the real service layer."""

import flet as ft
import pytest
from flet.controls.base_control import BaseControl

from app.main import build
from app.ui import shell
from app.ui.common import DENIED, GENERIC_ERROR, SESSION_ENDED, Ctx, call
from app.ui.login import login_view
from tests.fake_services import FakeServices


class FakePage:
    """Just enough of ft.Page for screens built outside a running app."""

    def __init__(self):
        """No controls and no dialogs yet."""
        self.controls, self.dialogs = [], []

    def update(self, *controls):
        """Nothing to redraw outside a running app."""

    def show_dialog(self, dialog):
        """Remember the dialog so a test can look at it."""
        self.dialogs.append(dialog)

    def pop_dialog(self):
        """Close the newest dialog, like Flet does."""
        return self.dialogs.pop() if self.dialogs else None


@pytest.fixture(autouse=True)
def no_live_page(monkeypatch):
    """Controls aren't on a real page in these tests, so their own update() does nothing."""
    monkeypatch.setattr(BaseControl, "update", lambda self: None)


def walk(control):
    """Every control inside a control tree, dialogs included."""
    yield control
    for child in [
        getattr(control, "content", None),
        *(getattr(control, "controls", None) or []),
        *(getattr(control, "actions", None) or []),
        getattr(control, "trailing", None),
    ]:
        if isinstance(child, ft.Control):
            yield from walk(child)


def button(root, text):
    """The button labelled `text` inside `root`."""
    return next(
        c
        for c in walk(root)
        if isinstance(c, (ft.FilledButton, ft.TextButton)) and c.content == text
    )


def signed_in(username):
    """A fake page showing the signed-in window for one preview user."""
    svc, page = FakeServices(), FakePage()
    build(page, svc)
    form = page.controls[0].content
    form.controls[2].value, form.controls[3].value = username, "preview-password"
    form.controls[-1].on_click(None)
    return svc, page


@pytest.mark.parametrize(
    "username, sections",
    [
        ("admin.ana", ["Members", "Payments", "Training plans", "Users"]),
        ("desk.ben", ["Members", "Payments"]),
        ("coach.cris", ["Members", "Training plans"]),
        ("member.dana", ["Payments", "Training plans"]),
        ("audit.eli", ["Members", "Payments", "Training plans", "Audit log"]),
    ],
)
def test_each_role_sees_only_its_sections(username, sections):
    """The menu is built from the service's permission answers."""
    _, page = signed_in(username)
    rail = page.controls[0].controls[0]
    assert [d.label for d in rail.destinations] == sections


def test_a_failed_login_shows_the_services_generic_message():
    """Same message whatever the reason, and the password box is cleared."""
    svc, done = FakeServices(), []
    view = login_view(svc, done.append)
    form = view.content
    form.controls[2].value, form.controls[3].value = "nobody", "wrong"
    form.controls[-1].on_click(None)
    assert done == [] and form.controls[4].value == "Invalid username or password."
    assert form.controls[3].value == ""


def test_refusals_and_unexpected_errors_show_only_short_messages():
    """Denied calls and internal errors never show details."""
    svc, page = FakeServices(), FakePage()
    ctx = Ctx(page, svc, svc.login("desk.ben", "x"), lambda m: None)
    assert call(ctx, svc.list_users, ctx.token) == (False, None)
    assert page.dialogs[-1].content.value == DENIED

    def broken(*args):
        """An internal failure with details an attacker would like to see."""
        raise RuntimeError("sqlite3.OperationalError: no such table: members")

    assert call(ctx, broken) == (False, None)
    assert page.dialogs[-1].content.value == GENERIC_ERROR


def test_a_user_deactivated_meanwhile_is_sent_back_to_sign_in():
    """The next service call ends the session and the sign-in screen replaces the window."""
    svc, page = signed_in("desk.ben")
    svc.set_user_active(svc.login("admin.ana", "x"), 2, False, "x")
    rail = page.controls[0].controls[0]
    rail.on_change(type("E", (), {"control": type("C", (), {"selected_index": 1})()})())
    assert isinstance(page.controls[0].content, ft.Column)  # the sign-in form
    assert page.controls[0].content.controls[4].value == SESSION_ENDED


def test_a_session_that_is_already_dead_never_shows_a_blank_window():
    """shell_view gives nothing back when whoami fails, so sign-in stays on screen."""
    svc, page, ended = FakeServices(), FakePage(), []
    assert shell.shell_view(page, svc, "not-a-token", ended.append) is None
    assert ended == [SESSION_ENDED]


def test_a_rejected_new_user_keeps_the_dialog_and_what_was_typed():
    """A short password is refused by the service; the admin fixes it without retyping."""
    svc, page = signed_in("admin.ana")
    rail = page.controls[0].controls[0]
    rail.on_change(type("E", (), {"control": type("C", (), {"selected_index": 3})()})())  # Users
    users = page.controls[0].controls[2].content
    button(users, "New user").on_click(None)
    dialog = page.dialogs[-1]
    name, password, role = dialog.content.controls
    name.value, password.value, role.value = "desk.fay", "short", "Front Desk"
    button(dialog, "Create").on_click(None)
    assert dialog in page.dialogs and name.value == "desk.fay"  # still open, still filled
    assert page.dialogs[-1].content.value == "Password must be 12 characters or more."
    password.value = "long-enough-password"  # fix it and save again
    button(dialog, "Create").on_click(None)
    assert dialog not in page.dialogs  # the form closes, not just the toast
    assert "desk.fay" in [u["username"] for u in svc.list_users(svc.login("admin.ana", "x"))]
