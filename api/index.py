import json
from datetime import datetime, timedelta

# Try to import optional dependencies
try:
    import yfinance as yf
    import pandas as pd
    import pytz
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

def get_market_data(target_date):
    """Fetch MNQ futures data from Yahoo Finance"""
    if not DEPENDENCIES_AVAILABLE:
        return {
            'error': 'Dependencies not available',
            'message': 'yfinance, pandas, or pytz not installed',
            'data': {'30s': [], '5m': [], '15m': []}
        }

    try:
        pacific = pytz.timezone('America/Los_Angeles')

        ticker = yf.Ticker("MNQ=F")
        end_date = target_date + timedelta(days=1)
        start_date = target_date

        data = ticker.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1m',
            prepost=True
        )

        if data.empty:
            return {
                'error': 'No data available',
                'message': 'Yahoo Finance typically only provides intraday data for the last 7 days.',
                'data': {'30s': [], '5m': [], '15m': []}
            }

        data.index = data.index.tz_convert('America/Los_Angeles')
        market_data = data.between_time('06:30', '13:00')

        if market_data.empty:
            market_data = data

        df = pd.DataFrame({
            'timestamp': market_data.index,
            'open': market_data['Open'],
            'high': market_data['High'],
            'low': market_data['Low'],
            'close': market_data['Close'],
            'volume': market_data['Volume']
        })

        df = df.reset_index(drop=True)

        thirty_sec_data = process_timeframe(df, 0.5)
        five_min_data = process_timeframe(df, 5)
        fifteen_min_data = process_timeframe(df, 15)

        return {
            'success': True,
            'data': {
                '30s': thirty_sec_data,
                '5m': five_min_data,
                '15m': fifteen_min_data
            }
        }

    except Exception as e:
        return {
            'error': 'Data fetch failed',
            'message': str(e),
            'data': {'30s': [], '5m': [], '15m': []}
        }

def process_timeframe(df, minutes):
    """Resample data to specified timeframe"""
    if not DEPENDENCIES_AVAILABLE:
        return []

    if minutes == 0.5:
        return create_30second_data(df)

    if minutes == 1:
        result = df.to_dict('records')
        # Convert pandas timestamps to ISO format
        for record in result:
            if 'timestamp' in record:
                record['timestamp'] = pd.Timestamp(record['timestamp']).isoformat()
        return result

    df_temp = df.set_index('timestamp')
    # Fixed deprecation warning
    df_resampled = df_temp.resample(f'{minutes}min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    result = df_resampled.reset_index().to_dict('records')
    # Convert pandas timestamps to ISO format
    for record in result:
        if 'timestamp' in record:
            record['timestamp'] = pd.Timestamp(record['timestamp']).isoformat()
    return result

def create_30second_data(df):
    """Create synthetic 30-second candles from 1-minute data"""
    if not DEPENDENCIES_AVAILABLE or df.empty:
        return []

    candles_30s = []

    for _, row in df.iterrows():
        timestamp = row['timestamp']
        o = row['open']
        h = row['high']
        l = row['low']
        c = row['close']
        v = row['volume']

        mid_price = (o + h + l + c) / 4

        candles_30s.append({
            'timestamp': pd.Timestamp(timestamp).isoformat(),
            'open': float(o),
            'high': float(max(h, mid_price)),
            'low': float(min(l, mid_price)),
            'close': float(mid_price),
            'volume': int(v // 2)
        })

        second_timestamp = pd.Timestamp(timestamp) + pd.Timedelta(seconds=30)

        candles_30s.append({
            'timestamp': second_timestamp.isoformat(),
            'open': float(mid_price),
            'high': float(max(h, mid_price)),
            'low': float(min(l, mid_price)),
            'close': float(c),
            'volume': int(v // 2)
        })

    return candles_30s

def handler(request):
    """Vercel serverless function with full yfinance functionality"""

    # Get the path and query parameters
    path = request.get('path', '')
    method = request.get('method', 'GET')
    query = request.get('query', {})

    if path == '/api/test':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'success',
                'message': 'Serverless function is working with full functionality!',
                'method': method,
                'path': path,
                'dependencies_available': DEPENDENCIES_AVAILABLE,
                'timestamp': datetime.now().isoformat()
            })
        }

    elif path == '/api/mnq-data':
        try:
            date_param = query.get('date', [None])[0] if isinstance(query.get('date'), list) else query.get('date')

            pacific = pytz.timezone('America/Los_Angeles') if DEPENDENCIES_AVAILABLE else None

            if date_param:
                try:
                    target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                except ValueError:
                    return {
                        'statusCode': 400,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': 'Invalid date format',
                            'message': 'Use YYYY-MM-DD format'
                        })
                    }
            else:
                if DEPENDENCIES_AVAILABLE and pacific:
                    target_date = datetime.now(pacific).date()
                    if target_date.weekday() >= 5:
                        target_date = target_date - timedelta(days=target_date.weekday() - 4)
                else:
                    target_date = datetime.now().date()

            market_data_result = get_market_data(target_date)

            if market_data_result.get('error'):
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': market_data_result['error'],
                        'message': market_data_result['message'],
                        'date': target_date.strftime('%Y-%m-%d'),
                        'data': market_data_result['data']
                    })
                }

            result = {
                'date': target_date.strftime('%Y-%m-%d'),
                'market_hours': {
                    'open': '06:30:00',
                    'close': '13:00:00',
                    'timezone': 'America/Los_Angeles'
                },
                'data': market_data_result['data']
            }

            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(result)
            }

        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Internal server error',
                    'message': str(e),
                    'data': {'30s': [], '5m': [], '15m': []}
                })
            }

    else:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Not found',
                'path': path,
                'available_endpoints': ['/api/test', '/api/mnq-data']
            })
        }