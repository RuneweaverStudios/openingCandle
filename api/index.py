from flask import Flask, request, jsonify, render_template
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

app = Flask(__name__)


@app.route('/')
def home():
    """Serve the main HTML page"""
    return render_template('dark_theme.html')

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

@app.route('/white-theme')
def white_theme():
    """White theme version of the application"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MNQ Futures Charts - White Theme</title>
    <script src="https://cdn.plot.ly/plotly-2.33.0.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #ffffff;
            color: #333333;
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #2c3e50;
            font-size: 32px;
            margin-bottom: 10px;
        }

        .header p {
            color: #6c757d;
            font-size: 16px;
        }

        .controls {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            align-items: center;
        }

        .control-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .control-group label {
            font-weight: 500;
            color: #495057;
        }

        input[type="date"] {
            padding: 10px;
            border: 2px solid #dee2e6;
            border-radius: 6px;
            font-size: 14px;
            background: white;
        }

        button {
            padding: 12px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        #generateBtn {
            background: #007bff;
            color: white;
        }

        #generateBtn:hover {
            background: #0056b3;
            transform: translateY(-1px);
        }

        #exportBtn {
            background: #28a745;
            color: white;
        }

        #exportBtn:hover {
            background: #218838;
            transform: translateY(-1px);
        }

        #widgetBtn {
            background: #17a2b8;
            color: white;
        }

        #widgetBtn:hover {
            background: #138496;
            transform: translateY(-1px);
        }

        #themeToggleBtn {
            background: #6c757d;
            color: white;
        }

        #themeToggleBtn:hover {
            background: #5a6268;
            transform: translateY(-1px);
        }

        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
            text-align: center;
            border-left: 4px solid #dc3545;
        }

        .loading {
            background: #e2e3e5;
            color: #495057;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
            text-align: center;
            font-style: italic;
        }

        .winrate-section {
            margin: 20px 0;
            padding: 20px;
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .winrate-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #dee2e6;
        }

        .winrate-header h3 {
            margin: 0;
            color: #2c3e50;
            font-size: 18px;
        }

        .refresh-btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.3s ease;
        }

        .refresh-btn:hover {
            background: #0056b3;
        }

        .winrate-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .winrate-loading {
            grid-column: 1 / -1;
            text-align: center;
            padding: 40px;
            color: #6c757d;
            font-style: italic;
        }

        .winrate-summary {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #e9ecef;
            text-align: center;
        }

        .winrate-overall {
            background: linear-gradient(135deg, #ffffff 0%, #f1f3f4 100%);
            color: #2c3e50;
            padding: 25px;
            border-radius: 6px;
            text-align: center;
            border: 1px solid #dee2e6;
        }

        .winrate-overall h4 {
            margin: 0 0 15px 0;
            font-size: 16px;
            color: #495057;
        }

        .winrate-percentage {
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }

        .winrate-percentage.good {
            color: #28a745;
        }

        .winrate-percentage.bad {
            color: #dc3545;
        }

        .winrate-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .winrate-stat {
            background: #e9ecef;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }

        .winrate-stat-value {
            font-size: 20px;
            font-weight: bold;
            display: block;
            color: #2c3e50;
        }

        .winrate-stat-label {
            font-size: 12px;
            color: #6c757d;
            margin-top: 5px;
        }

        .daily-breakdown {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #e9ecef;
        }

        .daily-breakdown h4 {
            margin: 0 0 15px 0;
            color: #2c3e50;
            font-size: 16px;
        }

        .daily-winrate-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #f1f3f4;
        }

        .daily-winrate-item:last-child {
            border-bottom: none;
        }

        .daily-date {
            font-weight: 500;
            color: #2c3e50;
        }

        .daily-candle {
            font-size: 12px;
            color: #6c757d;
            margin-left: 10px;
        }

        .daily-stats {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .winrate-badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            color: white;
        }

        .winrate-badge.good {
            background: #28a745;
        }

        .winrate-badge.bad {
            background: #dc3545;
        }

        .winrate-badge.neutral {
            background: #ffc107;
            color: #000;
        }

        .winrate-trades {
            font-size: 12px;
            color: #6c757d;
        }

        .charts-container {
            max-width: 1400px;
            margin: 0 auto;
            display: none;
        }

        .chart-section {
            margin-bottom: 40px;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border: 1px solid #e9ecef;
        }

        .chart-title {
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
            font-size: 20px;
            font-weight: 600;
        }

        .chart-controls {
            text-align: center;
            margin-bottom: 20px;
        }

        .share-btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s ease;
        }

        .share-btn:hover {
            background: #0056b3;
        }

        .chart {
            height: 500px;
            width: 100%;
            margin: 20px 0;
            border: 1px solid #dee2e6;
            border-radius: 6px;
        }

        .range-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .range-box {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #e9ecef;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .range-box:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }

        .range-box label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #495057;
            cursor: pointer;
        }

        .range-value {
            font-size: 24px;
            font-weight: bold;
            color: #6c757d;
            display: block;
            margin-top: 5px;
        }

        .theme-toggle {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f8f9fa;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            padding: 10px 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .theme-toggle:hover {
            background: #e9ecef;
            transform: translateY(-2px);
        }

        .theme-toggle span {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #495057;
        }

        @media (max-width: 768px) {
            .controls {
                flex-direction: column;
            }

            .winrate-header {
                flex-direction: column;
                gap: 10px;
                text-align: center;
            }

            .winrate-content {
                grid-template-columns: 1fr;
            }

            .winrate-stats {
                grid-template-columns: repeat(2, 1fr);
            }

            .theme-toggle {
                top: 10px;
                right: 10px;
                padding: 8px 12px;
            }
        }
    </style>
</head>
<body>
    <div class="theme-toggle">
        <span>🌓 Switch to Dark Theme</span>
    </div>

    <div class="header">
        <h1>📊 MNQ Futures Charts - White Theme</h1>
        <p>Micro Nasdaq Futures - Multi-Timeframe Analysis with Range Markers</p>
        <p style="margin-top: 10px; font-size: 14px; color: #6c757d;">
            <a href="/" style="color: #007bff; text-decoration: none;">← Back to Dark Theme</a>
        </p>
    </div>

    <div class="controls">
        <div class="control-group">
            <label for="date">Trading Date:</label>
            <input type="date" id="date">
        </div>
        <button onclick="generateCharts()" id="generateBtn">Generate Charts</button>
        <button onclick="exportAllCharts()" id="exportBtn">Export All Charts</button>
        <button onclick="openWidgetModal()" id="widgetBtn">Create Widget</button>
    </div>

    <div id="error" class="error" style="display: none;"></div>
    <div id="loading" class="loading" style="display: none;">Loading...</div>

    <!-- Winrate Analysis Section -->
    <div id="winrateSection" class="winrate-section" style="display: none;">
        <div class="winrate-header">
            <h3>📈 First Candle Strategy Performance</h3>
            <button onclick="refreshWinrate()" class="refresh-btn">🔄 Refresh</button>
        </div>
        <div id="winrateContent" class="winrate-content">
            <div class="winrate-loading">Loading winrate data...</div>
        </div>
    </div>

    <div class="charts-container" id="chartsContainer" style="display: none;">
        <div class="chart-section">
            <div class="chart-title">30-Second Chart</div>
            <div class="chart-controls">
                <button class="share-btn" onclick="openShareModal('30s')">Share & Embed</button>
            </div>
            <div class="range-info">
                <div class="range-box range-first">
                    <label>
                        <input type="checkbox" id="showFirst-30s" checked> First 30s Range
                    </label>
                    <span id="rangeFirst-30s" class="range-value">-</span>
                </div>
                <div class="range-box range-5min">
                    <label>
                        <input type="checkbox" id="show5min-30s" checked> 5 Minute Range
                    </label>
                    <span id="range5min-30s" class="range-value">-</span>
                </div>
                <div class="range-box range-15min">
                    <label>
                        <input type="checkbox" id="show15min-30s" checked> 15 Minute Range
                    </label>
                    <span id="range15min-30s" class="range-value">-</span>
                </div>
            </div>
            <div id="chart-30s" class="chart"></div>
        </div>

        <div class="chart-section">
            <div class="chart-title">5-Minute Chart</div>
            <div class="chart-controls">
                <button class="share-btn" onclick="openShareModal('5m')">Share & Embed</button>
            </div>
            <div class="range-info">
                <div class="range-box range-first">
                    <label>
                        <input type="checkbox" id="showFirst-5m" checked> First 30s Range
                    </label>
                    <span id="rangeFirst-5m" class="range-value">-</span>
                </div>
                <div class="range-box range-5min">
                    <label>
                        <input type="checkbox" id="show5min-5m" checked> 5 Minute Range
                    </label>
                    <span id="range5min-5m" class="range-value">-</span>
                </div>
                <div class="range-box range-15min">
                    <label>
                        <input type="checkbox" id="show15min-5m" checked> 15 Minute Range
                    </label>
                    <span id="range15min-5m" class="range-value">-</span>
                </div>
            </div>
            <div id="chart-5m" class="chart"></div>
        </div>

        <div class="chart-section">
            <div class="chart-title">15-Minute Chart</div>
            <div class="chart-controls">
                <button class="share-btn" onclick="openShareModal('15m')">Share & Embed</button>
            </div>
            <div class="range-info">
                <div class="range-box range-first">
                    <label>
                        <input type="checkbox" id="showFirst-15m" checked> First 30s Range
                    </label>
                    <span id="rangeFirst-15m" class="range-value">-</span>
                </div>
                <div class="range-box range-5min">
                    <label>
                        <input type="checkbox" id="show5min-15m" checked> 5 Minute Range
                    </label>
                    <span id="range5min-15m" class="range-value">-</span>
                </div>
                <div class="range-box range-15min">
                    <label>
                        <input type="checkbox" id="show15min-15m" checked> 15 Minute Range
                    </label>
                    <span id="range15min-15m" class="range-value">-</span>
                </div>
            </div>
            <div id="chart-15m" class="chart"></div>
        </div>
    </div>

    <!-- Share Modal -->
    <div id="shareModal" class="modal" style="display: none;">
        <div class="modal-content">
            <span class="close" onclick="closeShareModal()">&times;</span>
            <h2>Share & Embed Chart</h2>
            <div class="tabs">
                <button class="tab-btn active" onclick="showTab('download')">📥 Download</button>
                <button class="tab-btn" onclick="showTab('embed')">🔗 Embed</button>
            </div>
            <div id="downloadTab" class="tab-content">
                <h3>Download Chart as PNG</h3>
                <p>Right-click the chart and select "Save as image", or use the button below:</p>
                <button onclick="downloadChart()">Download PNG</button>
                <h3>Export All Charts</h3>
                <button onclick="exportAllCharts()">Export All as PNG</button>
            </div>
            <div id="embedTab" class="tab-content" style="display: none;">
                <h3>Embed Code</h3>
                <textarea id="embedCode" readonly style="width: 100%; height: 100px; font-family: monospace;"></textarea>
                <button onclick="copyEmbedCode()">Copy Code</button>
                <h3>Widget Embed</h3>
                <button onclick="openWidgetModal()">Create Advanced Widget</button>
            </div>
        </div>
    </div>

    <!-- Widget Modal -->
    <div id="widgetModal" class="modal" style="display: none;">
        <div class="modal-content">
            <span class="close" onclick="closeWidgetModal()">&times;</span>
            <h2>Create Widget</h2>
            <div class="widget-options">
                <label>
                    Layout:
                    <select id="widgetLayout">
                        <option value="side-by-side">Side by Side</option>
                        <option value="stacked">Stacked</option>
                    </select>
                </label>
                <label>
                    Theme:
                    <select id="widgetTheme">
                        <option value="dark">Dark Theme</option>
                        <option value="light">Light Theme</option>
                    </select>
                </label>
            </div>
            <div id="widgetPreview"></div>
            <button onclick="generateWidget()">Generate Widget</button>
        </div>
    </div>

    <script>
        // Theme toggle functionality
        function toggleTheme() {
            const currentUrl = window.location.pathname;
            if (currentUrl.includes('/white-theme')) {
                window.location.href = '/';
            } else {
                window.location.href = '/white-theme';
            }
        }

        // Add click handler to theme toggle
        document.querySelector('.theme-toggle').addEventListener('click', toggleTheme);

        // Show/hide loading
        function showLoading(show) {
            const loadingEl = document.getElementById('loading');
            loadingEl.style.display = show ? 'block' : 'none';
        }

        // Show error message
        function showError(message) {
            const errorEl = document.getElementById('error');
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }

        // Hide error message
        function hideError() {
            document.getElementById('error').style.display = 'none';
        }

        // Generate charts function
        async function generateCharts() {
            showLoading(true);
            hideError();

            const dateValue = document.getElementById('date').value;
            const dateParam = dateValue ? `?date=${dateValue}` : '';

            try {
                const response = await fetch(`/api/mnq-data${dateParam}`);
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                // Generate charts for each timeframe
                const timeframes = [
                    { id: '30s', label: '30-Second Chart' },
                    { id: '5m', label: '5-Minute Chart' },
                    { id: '15m', label: '15-Minute Chart' }
                ];

                for (const timeframe of timeframes) {
                    const chartData = data.data[timeframe.id] || [];
                    // Calculate ranges from data instead of expecting from backend
                    let ranges;
                    try {
                        ranges = calculateRanges(data.data);
                        console.log('Ranges calculated successfully:', ranges);
                    } catch (error) {
                        console.error('Error calculating ranges:', error);
                        ranges = createDefaultRanges();
                    }

                    // Defensive: Ensure ranges is valid
                    if (!ranges || typeof ranges !== 'object') {
                        console.warn('Invalid ranges object, using defaults');
                        ranges = createDefaultRanges();
                    }

                    if (chartData.length > 0) {
                        createChart(`chart-${timeframe.id}`, chartData, ranges, timeframe.id);
                        updateRangeInfo(ranges, timeframe.id);
                    }
                }

                // Show the charts container after successful generation
                document.getElementById('chartsContainer').style.display = 'block';

                // Show and load winrate data
                document.getElementById('winrateSection').style.display = 'block';
                loadWinrateData();

            } catch (error) {
                showError(`Error: ${error.message}`);
            } finally {
                showLoading(false);
                document.getElementById('generateBtn').disabled = false;
            }
        }

        // Winrate Functions
        async function loadWinrateData() {
            try {
                const response = await fetch('/api/winrate');
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                displayWinrateData(data);
            } catch (error) {
                document.getElementById('winrateContent').innerHTML =
                    `<div class="winrate-loading" style="color: #dc3545;">Error loading winrate data: ${error.message}</div>`;
            }
        }

        function refreshWinrate() {
            document.getElementById('winrateContent').innerHTML =
                '<div class="winrate-loading">Refreshing winrate data...</div>';
            loadWinrateData();
        }

        function displayWinrateData(data) {
            const winrateClass = data.overall_winrate >= 50 ? 'good' : 'bad';
            const overallColor = data.overall_winrate >= 50 ? '#28a745' : '#dc3545';

            let html = `
                <div class="winrate-overall">
                    <h4>Overall Win Rate (7 Days)</h4>
                    <div class="winrate-percentage ${winrateClass}" style="color: ${overallColor};">
                        ${data.overall_winrate}%
                    </div>
                    <div class="winrate-stats">
                        <div class="winrate-stat">
                            <span class="winrate-stat-value">${data.total_days}</span>
                            <span class="winrate-stat-label">Days</span>
                        </div>
                        <div class="winrate-stat">
                            <span class="winrate-stat-value">${data.winning_days}</span>
                            <span class="winrate-stat-label">Winning Days</span>
                        </div>
                        <div class="winrate-stat">
                            <span class="winrate-stat-value">${data.total_wins}</span>
                            <span class="winrate-stat-label">Total Wins</span>
                        </div>
                        <div class="winrate-stat">
                            <span class="winrate-stat-value">${data.total_losses}</span>
                            <span class="winrate-stat-label">Total Losses</span>
                        </div>
                    </div>
                </div>
            `;

            // Add daily breakdown
            if (data.daily_breakdown && data.daily_breakdown.length > 0) {
                html += '<div class="daily-breakdown"><h4>Daily Performance</h4>';

                data.daily_breakdown.forEach(day => {
                    const badgeClass = day.winrate >= 50 ? 'good' : (day.winrate > 45 ? 'neutral' : 'bad');
                    const candleIcon = day.first_candle.direction === 'up' ? '📈' : '📉';

                    html += `
                        <div class="daily-winrate-item">
                            <div>
                                <span class="daily-date">${day.date}</span>
                                <span class="daily-candle">${candleIcon} ${day.first_candle.range.toFixed(2)}</span>
                            </div>
                            <div class="daily-stats">
                                <span class="winrate-badge ${badgeClass}">${day.winrate}%</span>
                                <span class="winrate-trades">${day.trades} trades</span>
                            </div>
                        </div>
                    `;
                });

                html += '</div>';
            }

            document.getElementById('winrateContent').innerHTML = html;
        }

        // Update range info for specific timeframe
        function updateRangeInfo(ranges, timeframe) {
            if (!ranges || !ranges['first']) return;

            const rangeFirstText = `${ranges['first'].low} - ${ranges['first'].high} (Range: ${ranges['first'].range})`;
            const range5minText = `${ranges['5min'].low} - ${ranges['5min'].high} (Range: ${ranges['5min'].range})`;
            const range15minText = `${ranges['15min'].low} - ${ranges['15min'].high} (Range: ${ranges['15min'].range})`;

            // Update specific chart
            if (document.getElementById(`rangeFirst-${timeframe}`)) {
                document.getElementById(`rangeFirst-${timeframe}`).textContent = rangeFirstText;
            }
            if (document.getElementById(`range5min-${timeframe}`)) {
                document.getElementById(`range5min-${timeframe}`).textContent = range5minText;
            }
            if (document.getElementById(`range15min-${timeframe}`)) {
                document.getElementById(`range15min-${timeframe}`).textContent = range15minText;
            }
        }

        // Create chart with white theme styling
        function createChart(elementId, candleData, ranges, timeframe) {
            if (!candleData || candleData.length === 0) {
                document.getElementById(elementId).innerHTML = '<div style="text-align: center; padding: 50px; color: #6c757d;">No data available</div>';
                return;
            }

            // Convert timestamps to Pacific time for display
            const times = candleData.map(c => {
                const date = new Date(c.timestamp);
                return date;
            });
            const opens = candleData.map(c => c.open);
            const highs = candleData.map(c => c.high);
            const lows = candleData.map(c => c.low);
            const closes = candleData.map(c => c.close);
            const volumes = candleData.map(c => c.volume);

            // Determine first candle color for indicators
            const firstCandleClose = closes[0];
            const firstCandleOpen = opens[0];
            const isFirstCandleGreen = firstCandleClose >= firstCandleOpen;

            const candlestickTrace = {
                x: times,
                open: opens,
                high: highs,
                low: lows,
                close: closes,
                type: 'candlestick',
                name: 'MNQ',
                increasing: {line: {color: '#28a745'}},
                decreasing: {line: {color: '#dc3545'}},
                showlegend: true,
                visible: true
            };

            // Create volume trace for main chart only
            const volumeTrace = {
                x: times,
                y: volumes,
                type: 'bar',
                name: 'Volume',
                marker: {
                    color: volumes.map((vol, i) => {
                        return closes[i] >= opens[i] ? '#28a745' : '#dc3545';
                    }),
                    opacity: 0.2
                },
                yaxis: 'y2',
                xaxis: 'x',
                showlegend: true
            };

            // Create a faint candlestick trace specifically for the rangeslider
            const sliderCandlestickTrace = {
                x: times,
                open: opens,
                high: highs,
                low: lows,
                close: closes,
                type: 'candlestick',
                name: 'Slider Candles',
                increasing: {line: {color: 'rgba(40, 167, 69, 0.05)'}},
                decreasing: {line: {color: 'rgba(220, 53, 69, 0.05)'}},
                showlegend: false,
                visible: 'legendonly'
            };

            // Add range lines based on toggle states
            const shapes = [];
            const annotations = [];

            // Check toggle states for this specific chart
            const showFirst = document.getElementById(`showFirst-${timeframe}`)?.checked ?? true;
            const show5min = document.getElementById(`show5min-${timeframe}`)?.checked ?? true;
            const show15min = document.getElementById(`show15min-${timeframe}`)?.checked ?? true;

            // Defensive: Create safe range access variables
            const firstRange = ranges && ranges['first'] ? ranges['first'] : { high: 0, low: 0, range: '0' };
            const fiveMinRange = ranges && ranges['5min'] ? ranges['5min'] : { high: 0, low: 0, range: '0' };
            const fifteenMinRange = ranges && ranges['15min'] ? ranges['15min'] : { high: 0, low: 0, range: '0' };

            // First 30s candle range - show across the entire chart
            if (showFirst && ranges && ranges['first'] && ranges['first'].high > 0) {
                shapes.push(
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: ranges['first'].high,
                        y1: ranges['first'].high,
                        line: {color: '#dc3545', width: 3, dash: 'solid'}
                    },
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: ranges['first'].low,
                        y1: ranges['first'].low,
                        line: {color: '#dc3545', width: 3, dash: 'solid'}
                    }
                );
                // Left side annotation
                annotations.push({
                    x: 0.02,
                    y: 0.98,
                    xref: 'paper',
                    yref: 'paper',
                    text: `First 30s: ${ranges['first'].low}-${ranges['first'].high} (Range: ${ranges['first'].range})`,
                    showarrow: false,
                    font: {color: isFirstCandleGreen ? '#28a745' : '#dc3545', size: 14, weight: 'bold'},
                    xanchor: 'left',
                    yanchor: 'top',
                    bgcolor: 'rgba(248, 249, 250, 0.8)',
                    bordercolor: isFirstCandleGreen ? '#28a745' : '#dc3545',
                    borderwidth: 1,
                    borderpad: 4
                });
            }

            // 5-minute range lines
            if (show5min && fiveMinRange.high > 0) {
                shapes.push(
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: fiveMinRange.high,
                        y1: fiveMinRange.high,
                        line: {color: '#ffc107', width: 2, dash: 'solid'}
                    },
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: fiveMinRange.low,
                        y1: fiveMinRange.low,
                        line: {color: '#ffc107', width: 2, dash: 'solid'}
                    }
                );
                // Left side annotation
                annotations.push({
                    x: 0.02,
                    y: 0.02,
                    xref: 'paper',
                    yref: 'paper',
                    text: `5min: ${ranges['5min'].low}-${ranges['5min'].high} (Range: ${ranges['5min'].range})`,
                    showarrow: false,
                    font: {color: '#663300', size: 14, weight: 'bold'},
                    xanchor: 'left',
                    yanchor: 'bottom',
                    bgcolor: 'rgba(248, 249, 250, 0.8)',
                    bordercolor: '#ffc107',
                    borderwidth: 1,
                    borderpad: 4
                });
            }

            // 15-minute range lines
            if (show15min && fifteenMinRange.high > 0) {
                shapes.push(
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: fifteenMinRange.high,
                        y1: fifteenMinRange.high,
                        line: {color: '#6f42c1', width: 2, dash: 'solid'}
                    },
                    {
                        type: 'line',
                        x0: times[0],
                        x1: times[times.length - 1],
                        y0: fifteenMinRange.low,
                        y1: fifteenMinRange.low,
                        line: {color: '#6f42c1', width: 2, dash: 'solid'}
                    }
                );
                // Left side annotation
                annotations.push({
                    x: 0.02,
                    y: 0.06,
                    xref: 'paper',
                    yref: 'paper',
                    text: `15min: ${ranges['15min'].low}-${ranges['15min'].high} (Range: ${ranges['15min'].range})`,
                    showarrow: false,
                    font: {color: '#6f42c1', size: 14, weight: 'bold'},
                    xanchor: 'left',
                    yanchor: 'top',
                    bgcolor: 'rgba(248, 249, 250, 0.8)',
                    bordercolor: '#6f42c1',
                    borderwidth: 1,
                    borderpad: 4
                });
            }

            // White theme layout configuration
            const layout = {
                title: `MNQ Futures - ${timeframe.toUpperCase()} (${document.getElementById('date').value || new Date().toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'})} PT)`,
                titlefont: {color: '#2c3e50', size: 14},
                paper_bgcolor: '#ffffff',
                plot_bgcolor: '#ffffff',
                font: {color: '#2c3e50'},
                xaxis: {
                    rangeslider: {
                        visible: true,
                        yaxis: {rangemode: 'normal'},
                        bgcolor: 'rgba(233, 236, 239, 0.7)',
                        bordercolor: '#adb5bd',
                        borderwidth: 1
                    },
                    gridcolor: '#e9ecef',
                    type: 'date',
                    tickformat: '%H:%M', // Show time in HH:MM format
                    tickfont: {color: '#495057', size: 9},
                    showgrid: true,
                    dtick: 3600000, // Tick every hour
                    tick0: '06:30' // Start at 6:30 AM
                },
                yaxis: {
                    gridcolor: '#e9ecef',
                    tickfont: {color: '#495057', size: 10},
                    showgrid: true,
                    autorange: true
                },
                yaxis2: {
                    title: 'Volume',
                    titlefont: {color: '#495057', size: 12},
                    tickfont: {color: '#495757', size: 10},
                    overlaying: 'y',
                    side: 'right',
                    showgrid: false,
                    autorange: true
                },
                margin: {t: 50, r: 20, b: 60, l: 70}, // Increased top margin for title
                shapes: shapes,
                annotations: annotations
            };

            const config = {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['toImage', 'sendDataToCloud', 'editInChartStudio', 'lasso2d', 'select2d'],
                displaylogo: false,
                scrollZoom: true
            };

            Plotly.newPlot(elementId, [candlestickTrace, volumeTrace, sliderCandlestickTrace], layout, config);

            // Force a redraw to ensure proper sizing
            setTimeout(() => {
                Plotly.Plots.resize(elementId);
            }, 100);
        }

        // Export all charts functionality
        function exportAllCharts() {
            try {
                // Create export container
                const exportContainer = document.createElement('div');
                exportContainer.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: white;
                    z-index: 10000;
                    overflow-y: auto;
                    padding: 20px;
                    box-sizing: border-box;
                `;

                // Add title
                const title = document.createElement('h1');
                title.textContent = 'MNQ Futures Chart Export';
                title.style.cssText = 'text-align: center; color: #2c3e50; margin: 20px 0;';
                exportContainer.appendChild(title);

                // Add charts
                const chartIds = ['chart-30s', 'chart-5m', 'chart-15m'];
                const titles = ['30-Second Chart', '5-Minute Chart', '15-Minute Chart'];

                for (let i = 0; i < chartIds.length; i++) {
                    const chartSection = document.createElement('div');
                    chartSection.style.cssText = `
                        margin-bottom: 30px;
                        padding: 20px;
                        border: 1px solid #dee2e6;
                        border-radius: 8px;
                        background: white;
                    `;

                    const chartTitle = document.createElement('h3');
                    chartTitle.textContent = titles[i];
                    chartTitle.style.cssText = 'color: #2c3e50; text-align: center; margin: 15px 0; font-size: 18px;';
                    chartSection.appendChild(chartTitle);

                    // Clone the chart
                    const chartElement = document.getElementById(chartIds[i]);
                    const chartClone = chartElement.cloneNode(true);
                    chartClone.style.cssText = 'height: 400px; width: 100%; background: white;';
                    chartSection.appendChild(chartClone);

                    exportContainer.appendChild(chartSection);
                }

                // Add export instructions
                const instructions = document.createElement('div');
                instructions.innerHTML = `
                    <p style="color: #6c757d; text-align: center; margin-top: 30px;">
                        Use your browser's print function (Cmd+P or Ctrl+P) to save as PDF, or take screenshots
                    </p>
                    <button onclick="this.parentElement.parentElement.remove()" style="
                        display: block;
                        margin: 20px auto;
                        padding: 10px 20px;
                        background: #dc3545;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 16px;
                    ">Close Export View</button>
                `;
                exportContainer.appendChild(instructions);

                document.body.appendChild(exportContainer);

                // Redraw charts in the new container
                for (let i = 0; i < chartIds.length; i++) {
                    const chartClone = exportContainer.querySelectorAll('.plotly')[i];
                    if (window.Plotly && chartClone) {
                        // This will require re-plotting with white background
                        // For now, the clone should work for screenshots
                    }
                }

            } catch (error) {
                showError('Export failed: ' + error.message);
            }
        }

        // Share functionality
        function openShareModal(timeframe) {
            const modal = document.getElementById('shareModal');
            modal.style.display = 'block';
            showTab('download');
        }

        function closeShareModal() {
            document.getElementById('shareModal').style.display = 'none';
        }

        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

            // Show selected tab
            document.getElementById(tabName + 'Tab').style.display = 'block';
            event.target.classList.add('active');
        }

        // Widget functionality
        function openWidgetModal() {
            const modal = document.getElementById('widgetModal');
            modal.style.display = 'block';
            generateWidgetPreview();
        }

        function closeWidgetModal() {
            document.getElementById('widgetModal').style.display = 'none';
        }

        function generateWidgetPreview() {
            const layout = document.getElementById('widgetLayout').value;
            const theme = document.getElementById('widgetTheme').value;
            const preview = document.getElementById('widgetPreview');

            const html = `
                <div style="background: ${theme === 'dark' ? '#1a1a1a' : '#ffffff'}; padding: 15px; border-radius: 8px; max-width: 400px;">
                    <h4 style="color: ${theme === 'dark' ? '#ffffff' : '#2c3e50'};">Widget Preview</h4>
                    <p style="color: ${theme === 'dark' ? '#b0b0b0' : '#6c757d'};">Layout: ${layout}</p>
                    <p style="color: ${theme === 'dark' ? '#b0b0b0' : '#6c757d'};">Theme: ${theme}</p>
                </div>
            `;

            preview.innerHTML = html;
        }

        function generateWidget() {
            const layout = document.getElementById('widgetLayout').value;
            const theme = document.getElementById('widgetTheme').value;

            // Create widget HTML based on layout and theme
            const widgetHtml = createWidgetHtml(layout, theme);

            // Create blob and download
            const blob = new Blob([widgetHtml], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'mnq-widget.html';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            closeWidgetModal();
        }

        function createWidgetHtml(layout, theme) {
            const themeColors = theme === 'dark' ? {
                bg: '#1a1a1a',
                text: '#ffffff',
                border: '#444',
                header: '#2a2a2a'
            } : {
                bg: '#ffffff',
                text: '#2c3e50',
                border: '#dee2e6',
                header: '#f8f9fa'
            };

            return `<!DOCTYPE html>
<html>
<head>
    <title>MNQ Futures Widget</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.plot.ly/plotly-2.33.0.min.js"></script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: ${themeColors.bg};
            color: ${themeColors.text};
            min-height: 100vh;
        }
        .widget-container {
            max-width: 1200px;
            margin: 0 auto;
            ${layout === 'side-by-side' ? 'display: grid; grid-template-columns: 1fr 1fr; gap: 20px;' : ''}
        }
        .chart-wrapper {
            background: ${themeColors.header};
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 10px;
            border: 1px solid ${themeColors.border};
        }
        .chart-title {
            color: ${themeColors.text};
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
            text-align: center;
        }
        .chart {
            height: 300px;
            border-radius: 4px;
        }
        .range-info {
            display: flex;
            gap: 10px;
            font-size: 12px;
            color: ${themeColors.text};
        }
        .range-item {
            padding: 5px;
            background: ${themeColors.header};
            border-radius: 4px;
            text-align: center;
        }
        .theme-footer {
            text-align: center;
            padding: 10px;
            font-size: 12px;
            color: ${themeColors.text};
            border-top: 1px solid ${themeColors.border};
        }
    </style>
</head>
<body>
    <div class="widget-container">
        <div class="chart-wrapper">
            <div class="chart-title">30-Second Chart</div>
            <div id="widget-chart-30s" class="chart"></div>
            <div class="range-info">
                <div class="range-item">First 30s Range</div>
            </div>
        </div>
        <div class="chart-wrapper">
            <div class="chart-title">5-Minute Chart</div>
            <div id="widget-chart-5m" class="chart"></div>
            <div class="range-info">
                <div class="range-item">First 30s Range</div>
                <div class="range-item">5 Minute Range</div>
            </div>
        </div>
        <div class="chart-wrapper">
            <div class="chart-title">15-Minute Chart</div>
            <div id="widget-chart-15m" class="chart"></div>
            <div class="range-info">
                <div class="range-item">First 30s Range</div>
                <div class="range-item">5 Minute Range</div>
                <div class="range-item">15 Minute Range</div>
            </div>
        </div>
    </div>
    <div class="theme-footer">
        <p>Generated: ${new Date().toLocaleDateString()}</p>
    </div>

    <script>
        function downloadChart() {
            // Placeholder for individual chart download
            alert('Right-click on the chart and select "Save as image", or use "Print" from browser menu');
        }

        function copyEmbedCode() {
            const embedCode = document.getElementById('embedCode');
            embedCode.select();
            document.execCommand('copy');
            embedCode.blur();
            alert('Embed code copied to clipboard!');
        }

        // Range box click handler
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('.range-box').forEach(box => {
                box.addEventListener('click', function() {
                    const checkbox = this.querySelector('input[type="checkbox"]');
                    if (checkbox) {
                        checkbox.checked = !checkbox.checked;
                    }
                });
            });
        });
    </script>
</body>
</html>
    ''')

# Vercel serverless handler for builds system
def handler(environ, start_response):
    return app(environ, start_response)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)