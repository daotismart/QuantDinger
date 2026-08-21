from app.services.strategy_v2.storage import StrategyBacktestRepository


class _Cur:
    def __init__(self):
        self.sql = ''
        self.params = None

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return []

    def close(self):
        return None


class _Db:
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return self.cur

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_list_runs_filters_by_source_id_and_legacy_name(monkeypatch):
    cur = _Cur()
    monkeypatch.setattr(
        'app.services.strategy_v2.storage.get_db_connection',
        lambda: _Db(cur),
    )
    StrategyBacktestRepository().list_runs(
        user_id=7,
        source_id=22,
        source_name='Dual Moving Average',
        limit=10,
    )
    assert 'source_id = ?' in cur.sql
    assert 'regexp_replace' in cur.sql
    assert cur.params[0] == 7
    assert 22 in cur.params
    assert 'Dual Moving Average' in cur.params


def test_list_runs_source_id_only_without_name(monkeypatch):
    cur = _Cur()
    monkeypatch.setattr(
        'app.services.strategy_v2.storage.get_db_connection',
        lambda: _Db(cur),
    )
    StrategyBacktestRepository().list_runs(user_id=7, source_id=22, limit=10)
    assert 'regexp_replace' not in cur.sql
    assert cur.params[:2] == (7, 22)
