"""
K-line (OHLCV) API routes.
"""
from flask import jsonify, request
from app.openapi.blueprint import HumanBlueprint as Blueprint
from datetime import datetime
import traceback

from app.services.kline import KlineService
from app.utils.logger import get_logger
from app.services.market.watchlist import validate_watchlist_pair
from app.services.market_context import MarketContext, SUPPORTED_CRYPTO_EXCHANGE_IDS
from app.utils.request_guard import RequestGuardError, cache_key, guarded_cached

logger = get_logger(__name__)

kline_blp = Blueprint('kline', __name__)
kline_service = KlineService()


def _latest_kline_ttl(timeframe: str) -> int:
    tf = (timeframe or '').strip()
    return {
        '1m': 3,
        '3m': 4,
        '5m': 5,
        '15m': 8,
        '30m': 10,
        '1H': 10,
        '4H': 15,
        '1D': 30,
        '1W': 60,
        '1h': 10,
        '4h': 15,
        '1d': 30,
        '1w': 60,
    }.get(tf, 10)


def _guard_policy(timeframe: str, limit: int, before_time):
    if before_time:
        return {
            'ttl_sec': 300,
            'stale_ttl_sec': 1800,
            'timeout_sec': 25,
            'max_concurrent': 6,
        }
    ttl = _latest_kline_ttl(timeframe)
    if limit <= 10:
        return {
            'ttl_sec': ttl,
            'stale_ttl_sec': max(20, ttl * 4),
            'timeout_sec': 8,
            'max_concurrent': 10,
        }
    return {
        'ttl_sec': ttl,
        'stale_ttl_sec': max(60, ttl * 6),
        'timeout_sec': 25,
        'max_concurrent': 10,
    }


@kline_blp.route('/kline', methods=['GET'])
def get_kline():
    """
    Fetch OHLCV k-line bars.

    Query params:
        market: Market type (Crypto, USStock, Forex, Futures)
        symbol: Symbol or ticker
        timeframe: Bar size (1m, 5m, 15m, 30m, 1H, 4H, 1D, 1W)
        limit: Number of bars (default 300)
        before_time: Return bars before this Unix timestamp (optional)
    """
    try:
        market = (request.args.get('market', 'USStock') or '').strip()
        symbol = (request.args.get('symbol', '') or '').strip()
        timeframe = (request.args.get('timeframe', '1D') or '').strip()
        limit = int(request.args.get('limit', 300))
        limit = max(1, min(1000, limit))
        before_time = request.args.get('before_time') or request.args.get('beforeTime')
        exchange_id = (request.args.get('exchange_id') or request.args.get('exchangeId') or '').strip() or None
        market_type = (request.args.get('market_type') or request.args.get('marketType') or '').strip() or None
        instrument_id = (request.args.get('instrument_id') or request.args.get('instrumentId') or '').strip()
        if market == 'Crypto':
            context = MarketContext.from_mapping({
                'market': market,
                'symbol': symbol,
                'exchange_id': exchange_id,
                'market_type': market_type,
                'instrument_id': instrument_id,
                'timeframe': timeframe,
            })
            if context.exchange_id not in SUPPORTED_CRYPTO_EXCHANGE_IDS:
                return jsonify({'code': 0, 'msg': 'Unsupported crypto exchange', 'data': None}), 400
        
        if before_time:
            before_time = int(before_time)
        
        if not symbol:
            return jsonify({
                'code': 0,
                'msg': 'Missing symbol parameter',
                'data': None
            }), 400

        validation_err = validate_watchlist_pair(market, symbol)
        if validation_err:
            return jsonify({'code': 0, 'msg': validation_err, 'data': None}), 400
        
        logger.info(f"Requesting K-lines: {market}:{symbol}, timeframe={timeframe}, limit={limit}")
        
        policy = _guard_policy(timeframe, limit, before_time)
        klines = guarded_cached(
            cache_key("indicator_kline", market, symbol, timeframe, limit, before_time or "", exchange_id or "", market_type or ""),
            lambda: kline_service.get_kline(
                market=market,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                before_time=before_time,
                exchange_id=exchange_id,
                market_type=market_type
            ),
            ttl_sec=policy['ttl_sec'],
            stale_ttl_sec=policy['stale_ttl_sec'],
            timeout_sec=policy['timeout_sec'],
            namespace="indicator_kline",
            max_concurrent=policy['max_concurrent'],
        )
        
        if not klines:
            msg = 'No data found'
            if market == 'Forex' and timeframe == '1m':
                msg = 'Forex 1-minute data requires Tiingo paid subscription'
            elif market == 'Forex' and timeframe in ('1W', '1M'):
                msg = 'No weekly/monthly data available for this period'
            return jsonify({
                'code': 0,
                'msg': msg,
                'data': [],
                'hint': 'tiingo_subscription' if (market == 'Forex' and timeframe == '1m') else None
            })
        
        context = MarketContext.from_mapping({
            'market': market,
            'symbol': symbol,
            'exchange_id': exchange_id,
            'market_type': market_type,
            'instrument_id': instrument_id,
            'timeframe': timeframe,
        })
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': klines,
            'meta': {
                'market_context': context.as_dict(),
                'bar_count': len(klines),
            },
        })
        
    except RequestGuardError as e:
        return jsonify({
            'code': 0,
            'msg': str(e),
            'data': None
        }), e.status_code
    except Exception as e:
        logger.error(f"Failed to fetch K-lines: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to fetch kline data: {str(e)}',
            'data': None
        }), 500


@kline_blp.route('/kline/history', methods=['GET'])
def get_kline_history():
    """Fetch complete historical OHLCV (no 1000-bar cap).

    Query params:
        market: CNFutures / CNFuturesOptions / CNIndexFutures / CNIndexOptions
        symbol: e.g. RB0, rb2509, IF2509, m2509-C-2800
        timeframe: 1m/5m/15m/30m/1H/4H/1D/1W (daily recommended for full history)
        start_date / end_date: YYYY-MM-DD (CST calendar day, optional)
        start_time / end_time: Unix seconds (optional)
    """
    try:
        market = (request.args.get('market', 'CNFutures') or '').strip()
        symbol = (request.args.get('symbol', '') or '').strip()
        timeframe = (request.args.get('timeframe', '1D') or '').strip() or '1D'
        start_date = (request.args.get('start_date') or request.args.get('startDate') or '').strip() or None
        end_date = (request.args.get('end_date') or request.args.get('endDate') or '').strip() or None
        start_time_raw = request.args.get('start_time') or request.args.get('startTime')
        end_time_raw = request.args.get('end_time') or request.args.get('endTime')
        start_time = int(start_time_raw) if start_time_raw else None
        end_time = int(end_time_raw) if end_time_raw else None

        if not symbol:
            return jsonify({'code': 0, 'msg': 'Missing symbol parameter', 'data': None}), 400

        cn_markets = {
            'CNFutures', 'CNFuturesOptions', 'CNIndexFutures', 'CNIndexOptions', 'Futures',
        }
        if market not in cn_markets:
            return jsonify({
                'code': 0,
                'msg': f'history endpoint currently supports {sorted(cn_markets)}; got {market}',
                'data': None,
            }), 400

        validation_err = validate_watchlist_pair(market, symbol) if market != 'Futures' else None
        if validation_err:
            # Futures generic may reject CN codes via watchlist; allow CNFutures path only.
            if market.startswith('CN'):
                return jsonify({'code': 0, 'msg': validation_err, 'data': None}), 400

        from app.data_sources.cn_futures import resolve_history_symbol
        from app.markets.cn_futures import is_cn_derivative

        if market.startswith('CN') and not is_cn_derivative(symbol):
            return jsonify({
                'code': 0,
                'msg': f'Symbol {symbol!r} is not a recognized China futures/options code',
                'data': None,
            }), 400

        history_symbol, mode = resolve_history_symbol(symbol)
        logger.info(
            "Requesting full history: %s:%s tf=%s range=%s..%s (feed=%s/%s)",
            market, symbol, timeframe, start_date or start_time, end_date or end_time,
            history_symbol, mode,
        )

        rows = guarded_cached(
            cache_key(
                "cn_futures_history",
                market, symbol, timeframe,
                start_date or "", end_date or "",
                start_time or "", end_time or "",
            ),
            lambda: kline_service.get_history(
                market=market,
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                start_date=start_date,
                end_date=end_date,
            ),
            ttl_sec=300,
            stale_ttl_sec=1800,
            timeout_sec=60,
            namespace="cn_futures_history",
            max_concurrent=4,
        )

        if not rows:
            return jsonify({'code': 0, 'msg': 'No history found', 'data': [], 'meta': {
                'history_symbol': history_symbol,
                'mode': mode,
                'bar_count': 0,
            }})

        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': rows,
            'meta': {
                'market': market,
                'symbol': symbol,
                'history_symbol': history_symbol,
                'mode': mode,
                'timeframe': timeframe,
                'bar_count': len(rows),
                'start_time': rows[0]['time'] if rows else None,
                'end_time': rows[-1]['time'] if rows else None,
            },
        })
    except RequestGuardError as e:
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), e.status_code
    except Exception as e:
        logger.error("Failed to fetch history: %s", e)
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to fetch history: {str(e)}',
            'data': None,
        }), 500


# openapi-compat: legacy import name
kline_bp = kline_blp
