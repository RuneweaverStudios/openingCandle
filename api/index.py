from flask import Flask, request, jsonify, render_template
import json
import os
from datetime import datetime, timedelta

# Try to import optional dependencies
try:
    import yfinance as yf
    import pandas as pd
    import pytz
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

app = Flask(__name__)


@app.route('/')
def home():
    """Serve the main HTML page"""
    return render_template('dark_theme.html')


@app.route('/white-theme')
def white_theme():
    """Serve the white theme HTML page"""
    return render_template('white_theme.html')

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

def calculate_first_candle_winrate(days=7):
    """Calculate historical winrate of first candle strategy"""
    if not DEPENDENCIES_AVAILABLE:
        return {'error': 'Dependencies not available'}

    try:
        winrate_data = []
        pacific = pytz.timezone('America/Los_Angeles')

        for i in range(days):
            target_date = (datetime.now(pacific) - timedelta(days=i)).date()

            try:
                # Get data for the specific date
                market_data = yf.download('MNQ=F', start=target_date, end=target_date + timedelta(days=1),
                                       interval='1m', progress=False)

                if market_data.empty:
                    continue

                df = pd.DataFrame({
                    'timestamp': market_data.index,
                    'open': market_data['Open'],
                    'high': market_data['High'],
                    'low': market_data['Low'],
                    'close': market_data['Close'],
                    'volume': market_data['Volume']
                })

                df = df.reset_index(drop=True)

                # Create 30-second data
                candles_30s = create_30second_data(df)

                if len(candles_30s) < 2:
                    continue

                # Analyze first candle strategy
                first_candle = candles_30s[0]
                first_range = first_candle['high'] - first_candle['low']
                first_direction = 'up' if first_candle['close'] >= first_candle['open'] else 'down'

                wins = 0
                losses = 0

                # Check subsequent candles against first candle range
                for candle in candles_30s[1:]:
                    # Strategy: Price breaks first candle high/low
                    if candle['high'] > first_candle['high']:
                        if first_direction == 'up':
                            wins += 1
                        else:
                            losses += 1
                    elif candle['low'] < first_candle['low']:
                        if first_direction == 'down':
                            wins += 1
                        else:
                            losses += 1

                total_trades = wins + losses
                winrate = (wins / total_trades * 100) if total_trades > 0 else 0

                winrate_data.append({
                    'date': target_date.strftime('%Y-%m-%d'),
                    'first_candle': {
                        'open': round(first_candle['open'], 2),
                        'high': round(first_candle['high'], 2),
                        'low': round(first_candle['low'], 2),
                        'close': round(first_candle['close'], 2),
                        'range': round(first_range, 2),
                        'direction': first_direction
                    },
                    'trades': total_trades,
                    'wins': wins,
                    'losses': losses,
                    'winrate': round(winrate, 1)
                })

            except Exception as e:
                print(f"Error processing date {target_date}: {e}")
                continue

        # Calculate overall statistics
        if winrate_data:
            total_days = len(winrate_data)
            total_wins = sum(d['wins'] for d in winrate_data)
            total_losses = sum(d['losses'] for d in winrate_data)
            overall_winrate = sum(d['winrate'] for d in winrate_data) / total_days
            winning_days = sum(1 for d in winrate_data if d['winrate'] > 50)

            return {
                'overall_winrate': round(overall_winrate, 1),
                'winning_days': winning_days,
                'total_days': total_days,
                'total_wins': total_wins,
                'total_losses': total_losses,
                'daily_breakdown': winrate_data
            }
        else:
            return {'error': 'No data available for the past 7 days'}

    except Exception as e:
        return {'error': f'Failed to calculate winrate: {str(e)}'}

@app.route('/api/test', methods=['GET'])
def test():
    """Test endpoint with full yfinance functionality"""
    return jsonify({
        'status': 'success',
        'message': 'Serverless function is working with full functionality!',
        'dependencies_available': DEPENDENCIES_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/mnq-data', methods=['GET'])
def get_mnq_data():
    """Fetch MNQ futures data from Yahoo Finance"""
    try:
        date_param = request.args.get('date')

        pacific = pytz.timezone('America/Los_Angeles') if DEPENDENCIES_AVAILABLE else None

        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'Invalid date format',
                    'message': 'Use YYYY-MM-DD format'
                }), 400
        else:
            if DEPENDENCIES_AVAILABLE and pacific:
                target_date = datetime.now(pacific).date()
                if target_date.weekday() >= 5:
                    target_date = target_date - timedelta(days=target_date.weekday() - 4)
            else:
                target_date = datetime.now().date()

        market_data_result = get_market_data(target_date)

        if market_data_result.get('error'):
            return jsonify({
                'error': market_data_result['error'],
                'message': market_data_result['message'],
                'date': target_date.strftime('%Y-%m-%d'),
                'data': market_data_result['data']
            }), 404

        result = {
            'date': target_date.strftime('%Y-%m-%d'),
            'market_hours': {
                'open': '06:30:00',
                'close': '13:00:00',
                'timezone': 'America/Los_Angeles'
            },
            'data': market_data_result['data']
        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'data': {'30s': [], '5m': [], '15m': []}
        }), 500

@app.route('/api/winrate', methods=['GET'])
def get_winrate():
    """Get historical winrate for first candle strategy"""
    try:
        winrate_data = calculate_first_candle_winrate()
        return jsonify(winrate_data), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch winrate data',
            'message': str(e)
        }), 500


# Vercel serverless handler for builds
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))

