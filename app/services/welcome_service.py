"""Admin-configurable welcome text + banner for /start.

Same documented gap as the admin key store: this store is in-memory
by default. In production main.py wiring must replace it with a
DB-backed store, or a custom welcome/banner is lost on restart and
is not shared between workers. The service interface is store-shaped
so that replacement is a wiring change, not a handler rewrite.

Security: a template is never a secret, but it is admin input, so
rendering (formatters.welcome_text) escapes names/usernames and
keeps only a safe tag set. A banner is a Telegram file_id set by an
admin from a photo they send; file_ids are never echoed back in
full in confirmations (the confirmation is just "Banner tersimpan").
No channel-join, forced-join, or verification-access content lives
here or anywhere in the welcome flow — that content was explicitly
replaced by a welcome message.
"""
from __future__ import annotations

MAX_TEMPLATE_CHARS = 2000


class WelcomeStore:
    """In-memory welcome template + banner photo file_id."""

    def __init__(self):
        self._template: str | None = None
        self._banner_photo_file_id: str | None = None

    @property
    def template(self) -> str | None:
        return self._template

    @property
    def banner_photo_file_id(self) -> str | None:
        return self._banner_photo_file_id

    def set_template(self, template: str) -> None:
        if not isinstance(template, str) or not template.strip():
            raise ValueError("Sambutan tidak boleh kosong.")
        if len(template) > MAX_TEMPLATE_CHARS:
            raise ValueError(
                f"Sambutan terlalu panjang (maks {MAX_TEMPLATE_CHARS} karakter).")
        self._template = template.strip()

    def set_banner(self, file_id: str) -> None:
        if not isinstance(file_id, str) or not file_id.strip():
            raise ValueError("Banner tidak valid.")
        self._banner_photo_file_id = file_id.strip()

    def clear_banner(self) -> None:
        self._banner_photo_file_id = None

    def reset(self) -> None:
        self._template = None
        self._banner_photo_file_id = None

    def render(self, *, name: str = "", username: str = "",
               display_name: str = "OktaScrape") -> str:
        from ..bot.formatters import welcome_text

        return welcome_text(name, username, display_name=display_name,
                            template=self._template)


class WelcomeInputState:
    """Which admins are mid-way through sending a template / banner photo."""

    def __init__(self):
        self._awaiting_template: set[int] = set()
        self._awaiting_banner: set[int] = set()

    def start_template(self, admin_id: int) -> None:
        self._awaiting_template.add(admin_id)

    def start_banner(self, admin_id: int) -> None:
        self._awaiting_banner.add(admin_id)

    def cancel(self, admin_id: int) -> None:
        self._awaiting_template.discard(admin_id)
        self._awaiting_banner.discard(admin_id)

    def is_awaiting_template(self, admin_id: int) -> bool:
        return admin_id in self._awaiting_template

    def is_awaiting_banner(self, admin_id: int) -> bool:
        return admin_id in self._awaiting_banner


# Process-wide default store, shared by handlers in the same (bot) process.
WELCOME_STORE = WelcomeStore()
