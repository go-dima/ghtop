# ghtop/screens/orgs.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import ListItem, ListView, Static

from ghtop.gh import gh, GHError
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


@dataclass
class OrgItem:
    login: str
    is_you: bool = False
    is_pinned: bool = False

    def label(self) -> str:
        pin = "★ " if self.is_pinned else "  "
        you = " [you]" if self.is_you else ""
        return f"{pin}{self.login}{you}"


class OrgScreen(Screen):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select", show=False, priority=True),
        Binding("s", "select", "Select"),
        Binding("p", "pin", "Pin"),
        Binding("q", "quit_app", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield ListView(id="org-list")
        yield Static("", id="empty-state")
        yield StatusBar("↑↓ navigate  Enter select  p pin  q quit")

    async def on_mount(self) -> None:
        self.query_one(AppHeader).breadcrumb = "ghtop"
        await self._load_orgs()

    async def _load_orgs(self) -> None:
        try:
            orgs_raw, user_raw = await asyncio.gather(
                gh("api", "/user/orgs", "--paginate"),
                gh("api", "/user"),
            )
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        orgs: list[OrgItem] = []
        org_logins: set[str] = set()

        for org in (orgs_raw or []):
            login = org["login"]
            org_logins.add(login)
            orgs.append(OrgItem(
                login=login,
                is_pinned=(login == self.app.config.pinned_org and
                           not self.app.config.pinned_repo),
            ))

        # Add personal account (deduplicate if already in orgs list)
        user_login = (user_raw or {}).get("login")
        if user_login:
            if user_login in org_logins:
                for item in orgs:
                    if item.login == user_login:
                        item.is_you = True
            else:
                orgs.append(OrgItem(login=user_login, is_you=True))

        list_view = self.query_one("#org-list", ListView)
        if not orgs:
            self.query_one("#empty-state", Static).update(
                "No organizations found. Make sure you are authenticated: gh auth status"
            )
            return

        self._orgs = orgs
        for item in orgs:
            list_view.append(ListItem(Static(item.label())))

        pinned_idx = next(
            (i for i, o in enumerate(orgs) if o.is_pinned), None
        )
        initial_idx = pinned_idx if pinned_idx is not None else 0

        def _init() -> None:
            list_view.index = initial_idx
            list_view.focus()

        self.call_after_refresh(_init)

    def action_select(self) -> None:
        idx = self.query_one(ListView).index
        if idx is None or not hasattr(self, "_orgs"):
            return
        org = self._orgs[idx]
        from ghtop.screens.repos import ReposScreen
        self.app.push_screen(ReposScreen(org.login))

    def action_pin(self) -> None:
        idx = self.query_one(ListView).index
        if idx is None or not hasattr(self, "_orgs"):
            return
        org = self._orgs[idx]
        if org.is_pinned:
            self.app.config.pinned_org = None
            org.is_pinned = False
        else:
            for o in self._orgs:
                o.is_pinned = False
            self.app.config.pinned_org = org.login
            self.app.config.pinned_repo = None
            org.is_pinned = True
        self.app._save_config()
        self._refresh_list()

    def _refresh_list(self) -> None:
        list_view = self.query_one("#org-list", ListView)
        items = list(list_view.query(ListItem))
        for i, item in enumerate(items):
            item.query_one(Static).update(self._orgs[i].label())

    def action_cursor_up(self) -> None:
        self.query_one(ListView).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(ListView).action_cursor_down()

    def action_quit_app(self) -> None:
        self.app.exit()
