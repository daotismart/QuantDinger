"""Chart display preferences: candle color scheme (green-up vs red-up)."""

from __future__ import annotations

from app.services.user_preferences import (
    DEFAULT_CHART_PREFERENCES,
    normalize_candle_color_scheme,
    update_chart_preferences,
)


class _Cursor:
    def __init__(self, store: dict):
        self.store = store
        self._last = None

    def execute(self, sql, params=None):
        text = " ".join(str(sql).split())
        if "ADD COLUMN" in text.upper():
            self._last = None
            return
        if text.startswith("SELECT chart_preferences"):
            self._last = {"chart_preferences": self.store.get("chart_preferences", "")}
            return
        if text.startswith("UPDATE qd_users SET chart_preferences"):
            self.store["chart_preferences"] = params[0]
            self._last = None
            return
        self._last = None

    def fetchone(self):
        return self._last

    def close(self):
        return None


class _Db:
    def __init__(self, store: dict):
        self.store = store

    def cursor(self):
        return _Cursor(self.store)

    def commit(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_normalize_candle_color_scheme_aliases():
    assert normalize_candle_color_scheme("red_up") == "red_up"
    assert normalize_candle_color_scheme("RED-UP") == "red_up"
    assert normalize_candle_color_scheme("cn") == "red_up"
    assert normalize_candle_color_scheme("green_down") == "red_up"
    assert normalize_candle_color_scheme("green_up") == "green_up"
    assert normalize_candle_color_scheme("western") == "green_up"
    assert normalize_candle_color_scheme("") == "green_up"
    assert normalize_candle_color_scheme("nope") == "green_up"


def test_update_chart_preferences_persists_red_up(monkeypatch):
    store = {"chart_preferences": ""}
    monkeypatch.setattr(
        "app.services.user_preferences.get_db_connection",
        lambda: _Db(store),
    )
    saved = update_chart_preferences(7, {"candleColorScheme": "red_up"})
    assert saved == {"candle_color_scheme": "red_up"}
    assert '"red_up"' in store["chart_preferences"]


def test_default_chart_preferences_are_green_up():
    assert DEFAULT_CHART_PREFERENCES["candle_color_scheme"] == "green_up"
