"""The screens against the preview stub: each role sees only its sections, a refused call shows a short
message instead of crashing, and a session that ends sends the user back to sign-in. These test the
interface only; the authorization matrix test (test_authz_matrix.py) tests the real service layer."""
import flet as ft
import pytest
from flet.controls.base_control import BaseControl

from app.ui import shell
from app.ui.common import DENIED, SESSION_ENDED, Ctx, call
from app.ui.login import login_view
from tests.fake_services import FakeServices


class FakePage:
    """Just enough of ft.Page for screens built outside a running app."""

    def __init__(self):
        self.dialogs, self.updates = [], 0

    def update(self, *controls):
        self.updates += 1

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None


@pytest.fixture(autouse=True)
def no_live_page(monkeypatch):
    monkeypatch.setattr(BaseControl, "update", lambda self: None)  # controls aren't on a real page here


def texts(control):
    """Every piece of text inside a control tree."""
    found = []

    def walk(c):
        if isinstance(c, ft.Text) and c.value:
            found.append(c.value)
        for child in [getattr(c, "content", None), *(getattr(c, "controls", None) or []),
                      *(getattr(c, "destinations", None) or []), getattr(c, "trailing", None)]:
            if isinstance(child, (ft.Control, ft.NavigationRailDestination)):
                walk(child)
        if isinstance(c, ft.NavigationRailDestination):
            found.append(c.label)
    walk(control)
    return found


@pytest.mark.parametrize("username, sections", [
    ("admin.ana", ["Members", "Payments", "Training plans", "Users"]),
    ("desk.ben", ["Members", "Payments"]),
    ("coach.cris", ["Members", "Training plans"]),
    ("member.dana", ["Payments", "Training plans"]),
    ("audit.eli", ["Members", "Payments", "Training plans", "Audit log"]),
])
def test_each_role_sees_only_its_sections(username, sections):
    svc, page = FakeServices(), FakePage()
    token = svc.login(username, "preview-password")
    window = shell.shell_view(page, svc, token, lambda msg: None)
    rail = window.controls[0]
    assert [d.label for d in rail.destinations] == sections


def test_a_failed_login_shows_the_services_generic_message():
    svc, signed_in = FakeServices(), []
    view = login_view(svc, signed_in.append)
    column = view.content
    username, password = column.controls[2], column.controls[3]
    username.value, password.value = "nobody", "wrong"
    column.controls[-1].on_click(None)
    assert signed_in == [] and "Invalid username or password." in texts(view) and password.value == ""


def test_a_refused_call_shows_a_short_message_and_an_ended_session_goes_to_sign_in():
    svc, page, ended = FakeServices(), FakePage(), []
    token = svc.login("desk.ben", "preview-password")
    ctx = Ctx(page, svc, token, ended.append)
    assert call(ctx, svc.list_users, token) is None                        # Front Desk may not manage users
    assert page.dialogs[-1].content.value == DENIED
    svc.set_user_active(svc.login("admin.ana", "preview-password"), 2, False, "x")  # deactivated meanwhile
    assert call(ctx, svc.list_records, token, "members") is None and ended == [SESSION_ENDED]


def test_unexpected_errors_never_show_details():
    svc, page = FakeServices(), FakePage()
    ctx = Ctx(page, svc, svc.login("admin.ana", "preview-password"), lambda m: None)

    def broken(*args):
        raise RuntimeError("sqlite3.OperationalError: no such table: members")
    assert call(ctx, broken) is None
    assert page.dialogs[-1].content.value == "Something went wrong. Please try again."
