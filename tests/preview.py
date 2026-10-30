"""Run the screens with in-memory preview data: python -m tests.preview

For building and showing the interface before the backend exists. It is not part of the real
app, and the preview accounts accept any password.
"""

import flet as ft

from app.main import build
from tests.fake_services import FakeServices

if __name__ == "__main__":
    ft.run(lambda page: build(page, FakeServices()))
