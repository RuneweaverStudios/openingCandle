from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["null", "file://", "*"]}})

# Vercel serverless handler
def handler(environ, start_response):
    return app(environ, start_response)

@app.route('/')
def home():
    """Serve the main HTML file"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MNQ Futures Charts</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #1a1a1a; color: #ffffff; }
        .header { text-align: center; margin-bottom: 30px; }
        .controls { display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; flex-wrap: wrap; }
        .control-group { display: flex; flex-direction: column; align-items: center; gap: 5px; }
        .control-group label { font-size: 14px; font-weight: bold; }
        .control-group input, .control-group select { padding: 8px; border-radius: 4px; border: 1px solid #444; background-color: #2a2a2a; color: #ffffff; }
        button { padding: 10px 20px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background-color: #0056b3; }
        button:disabled { background-color: #666; cursor: not-allowed; }
        .chart-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); gap: 20px; }
        .chart { background-color: #2a2a2a; border-radius: 8px; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        .chart h3 { margin-top: 0; margin-bottom: 15px; text-align: center; color: #4CAF50; }
        .toggle-container { display: flex; justify-content: center; gap: 20px; margin-top: 10px; }
        .toggle-container label { display: flex; align-items: center; gap: 5px; cursor: pointer; }
        .status { text-align: center; margin: 20px 0; padding: 10px; border-radius: 4px; }
        .status.error { background-color: #f8d7da; color: #721c24; }
        .status.success { background-color: #d4edda; color: #155724; }
        .loading { text-align: center; color: #ffffff; }
        .export-btn { padding: 8px 16px; background-color: #28a745; font-size: 14px; margin: 0 5px; }
        .export-btn:hover { background-color: #1e7e34; }
    </style>
</head>
<body>
    <div class="header">
        <h1>MNQ Futures Charts</h1>
        <p>Micro Nasdaq-100 Futures with Opening Range Markers</p>
    </div>

    <div class="controls">
        <div class="control-group">
            <label for="date">Select Date:</label>
            <input type="date" id="date" max="">
        </div>
        <button id="generateBtn" onclick="generateCharts()">Generate Charts</button>
    </div>

    <div id="status" class="status" style="display: none;"></div>

    <div id="loading" class="loading" style="display: none;">
        <p>Loading MNQ data from Yahoo Finance...</p>
    </div>

    <div id="charts" class="chart-container" style="display: none;">
        <div class="chart">
            <h3>30-Second Chart</h3>
            <div id="chart-30s"></div>
            <div class="toggle-container">
                <label>
                    <input type="checkbox" id="toggle-30s-5min" checked> 5-min Range
                </label>
                <label>
                    <input type="checkbox" id="toggle-30s-15min" checked> 15-min Range
                </label>
            </div>
        </div>
        <div class="chart">
            <h3>5-Minute Chart</h3>
            <div id="chart-5m"></div>
            <div class="toggle-container">
                <label>
                    <input type="checkbox" id="toggle-5m-5min" checked> 5-min Range
                </label>
                <label>
                    <input type="checkbox" id="toggle-5m-15min" checked> 15-min Range
                </label>
            </div>
        </div>
        <div class="chart">
            <h3>15-Minute Chart</h3>
            <div id="chart-15m"></div>
            <div class="toggle-container">
                <label>
                    <input type="checkbox" id="toggle-15m-5min" checked> 5-min Range
                </label>
                <label>
                    <input type="checkbox" id="toggle-15m-15min" checked> 15-min Range
                </label>
            </div>
        </div>
    </div>

    <script>
        // Set date input to today's date in Pacific timezone and constrain to not allow future dates
        function setDateToPacificToday() {
            const now = new Date();
            const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
            const pacificTime = new Date(utc - 480 * 60000); // UTC-8 for Pacific
            const dayOfWeek = pacificTime.getDay();

            let targetDate = new Date(pacificTime);

            // If weekend, go back to Friday
            if (dayOfWeek === 0) { // Sunday
                targetDate.setDate(targetDate.getDate() - 2);
            } else if (dayOfWeek === 6) { // Saturday
                targetDate.setDate(targetDate.getDate() - 1);
            }

            document.getElementById('date').value = targetDate.toISOString().split('T')[0];
            document.getElementById('date').max = targetDate.toISOString().split('T')[0];
        }

        function showStatus(message, isError = false) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = isError ? 'status error' : 'status success';
            statusDiv.style.display = 'block';
        }

        function setLoading(isLoading) {
            document.getElementById('loading').style.display = isLoading ? 'block' : 'none';
            document.getElementById('generateBtn').disabled = isLoading;
        }

        async function generateCharts() {
            const date = document.getElementById('date').value;
            if (!date) {
                showStatus('Please select a date', true);
                return;
            }

            setLoading(true);
            showStatus('Fetching MNQ futures data...', false);
            document.getElementById('charts').style.display = 'none';

            try {
                const response = await fetch(`/api/mnq-data?date=${date}`);

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                displayCharts(data);
                showStatus(`Successfully loaded ${data.date} MNQ futures data`, false);

            } catch (error) {
                console.error('Error:', error);
                showStatus(`Error: ${error.message}`, true);
            } finally {
                setLoading(false);
            }
        }

        function displayCharts(data) {
            const timeframes = ['30s', '5m', '15m'];
            timeframes.forEach(timeframe => {
                const chartData = data.data[timeframe];
                if (chartData && chartData.length > 0) {
                    createCandlestickChart(`chart-${timeframe}`, chartData, data.date, timeframe);
                }
            });
            document.getElementById('charts').style.display = 'grid';
        }

        function createCandlestickChart(divId, data, date, timeframe) {
            const timestamps = data.map(d => new Date(d.timestamp));
            const opens = data.map(d => d.open);
            const highs = data.map(d => d.high);
            const lows = data.map(d => d.low);
            const closes = data.map(d => d.close);
            const volumes = data.map(d => d.volume);

            // Calculate ranges
            const first5Min = timeframe === '5m' ? data[0] : data.slice(0, 10)[0]; // First 5-min candle or equivalent in 30s
            const first15Min = timeframe === '15m' ? data[0] : data.slice(0, 30)[0]; // First 15-min candle or equivalent in 30s

            const range5Min = first5Min ? { high: first5Min.high, low: first5Min.low } : null;
            const range15Min = first15Min ? { high: first15Min.high, low: first15Min.low } : null;

            const candlestick = {
                x: timestamps,
                open: opens,
                high: highs,
                low: lows,
                close: closes,
                type: 'candlestick',
                name: 'MNQ',
                increasing: { line: { color: '#00ff00' } },
                decreasing: { line: { color: '#ff0000' } }
            };

            const volume = {
                x: timestamps,
                y: volumes,
                type: 'bar',
                name: 'Volume',
                yaxis: 'y2',
                marker: { color: 'rgba(128, 128, 128, 0.5)' }
            };

            const layout = {
                title: `MNQ Futures - ${timeframe.toUpperCase()} Chart - ${date}`,
                xaxis: {
                    title: 'Time (Pacific)',
                    type: 'date',
                    rangeslider: { visible: true }
                },
                yaxis: { title: 'Price' },
                yaxis2: {
                    title: 'Volume',
                    overlaying: 'y',
                    side: 'right',
                    showgrid: false
                },
                template: 'plotly_dark',
                dragmode: 'zoom',
                showlegend: true,
                legend: { x: 0, y: 1 },
                shapes: [],
                annotations: []
            };

            // Add range shapes and annotations
            if (range5Min) {
                const showRange5Min = document.getElementById(`toggle-${timeframe}-5min`).checked;
                if (showRange5Min) {
                    layout.shapes.push({
                        type: 'rect',
                        x0: timestamps[0],
                        x1: timestamps[Math.min(59, timestamps.length - 1)], // Show for first hour
                        y0: range5Min.low,
                        y1: range5Min.high,
                        fillcolor: 'rgba(0, 123, 255, 0.2)',
                        line: { color: 'rgba(0, 123, 255, 0.5)' },
                        layer: 'below'
                    });
                    layout.annotations.push({
                        x: timestamps[0],
                        y: range5Min.high,
                        text: `5m Range: ${range5Min.low.toFixed(2)}-${range5Min.high.toFixed(2)}`,
                        showarrow: true,
                        arrowhead: 2,
                        bgcolor: 'rgba(0, 123, 255, 0.8)',
                        font: { color: 'white', size: 10 }
                    });
                }
            }

            if (range15Min) {
                const showRange15Min = document.getElementById(`toggle-${timeframe}-15min`).checked;
                if (showRange15Min) {
                    layout.shapes.push({
                        type: 'rect',
                        x0: timestamps[0],
                        x1: timestamps[Math.min(59, timestamps.length - 1)], // Show for first hour
                        y0: range15Min.low,
                        y1: range15Min.high,
                        fillcolor: 'rgba(255, 165, 0, 0.2)',
                        line: { color: 'rgba(255, 165, 0, 0.5)' },
                        layer: 'below'
                    });
                    layout.annotations.push({
                        x: timestamps[Math.min(29, timestamps.length - 1)],
                        y: range15Min.high,
                        text: `15m Range: ${range15Min.low.toFixed(2)}-${range15Min.high.toFixed(2)}`,
                        showarrow: true,
                        arrowhead: 2,
                        bgcolor: 'rgba(255, 165, 0, 0.8)',
                        font: { color: 'white', size: 10 }
                    });
                }
            }

            const config = {
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
            };

            Plotly.newPlot(divId, [candlestick, volume], layout, config);
        }

        // Toggle range visibility
        document.addEventListener('change', function(e) {
            if (e.target.id && e.target.id.startsWith('toggle-')) {
                generateCharts(); // Regenerate charts with new toggle states
            }
        });

        // Initialize date on page load
        setDateToPacificToday();

        // Generate charts for today by default
        window.addEventListener('load', function() {
            setTimeout(generateCharts, 500);
        });
    </script>
</body>
</html>'''

@app.route('/api/mnq-data')
def get_mnq_data():
    """Fetch MNQ futures data from Yahoo Finance"""
    date = request.args.get('date')  # Format: YYYY-MM-DD

    # Convert date to Pacific timezone and handle market hours
    pacific = pytz.timezone('America/Los_Angeles')
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        target_date = datetime.now(pacific).date()
        # If today is weekend, go back to Friday
        if target_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            target_date = target_date - timedelta(days=target_date.weekday() - 4)

    try:
        # Use Yahoo Finance for MNQ futures
        ticker = yf.Ticker("MNQ=F")

        # Get intraday data for the specified date
        # Yahoo Finance provides limited intraday data (usually last 7 days)
        end_date = target_date + timedelta(days=1)  # Add 1 day for end date
        start_date = target_date

        # Get 1-minute intraday data
        data = ticker.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1m',
            prepost=True  # Include pre/post market
        )

        if data.empty:
            return jsonify({'error': 'No data found for this date. Yahoo Finance typically only provides intraday data for the last 7 days.'}), 404

        # Convert to Pacific timezone
        data.index = data.index.tz_convert('America/Los_Angeles')

        # Filter for regular market hours (6:30 AM to 1:00 PM Pacific)
        market_data = data.between_time('06:30', '13:00')

        if market_data.empty:
            # If no regular market data, use what we have
            market_data = data

        # Prepare data with the correct column names
        df = pd.DataFrame({
            'timestamp': market_data.index,
            'open': market_data['Open'],
            'high': market_data['High'],
            'low': market_data['Low'],
            'close': market_data['Close'],
            'volume': market_data['Volume']
        })

        # Reset index to make timestamp a column
        df = df.reset_index(drop=True)

        # Prepare response with different timeframes
        thirty_sec_data = process_timeframe(df, 0.5)
        five_min_data = process_timeframe(df, 5)
        fifteen_min_data = process_timeframe(df, 15)

        result = {
            'date': target_date.strftime('%Y-%m-%d'),
            'market_hours': {
                'open': '06:30:00',
                'close': '13:00:00',
                'timezone': 'America/Los_Angeles'
            },
            'data': {
                '30s': thirty_sec_data,
                '5m': five_min_data,
                '15m': fifteen_min_data
            }
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'Error fetching data: {str(e)}'}), 500

def process_timeframe(df, minutes):
    """Resample data to specified timeframe"""
    if minutes == 0.5:  # 30 seconds
        # Create synthetic 30-second data from 1-minute data
        return create_30second_data(df)

    if minutes == 1:
        # Use original 1-minute data
        return df.to_dict('records')

    # Set timestamp as index for resampling
    df_temp = df.set_index('timestamp')

    # Resample to specified timeframe
    df_resampled = df_temp.resample(f'{minutes}T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    return df_resampled.reset_index().to_dict('records')

def create_30second_data(df):
    """Create synthetic 30-second candles from 1-minute data"""
    if df.empty:
        return []

    candles_30s = []

    for _, row in df.iterrows():
        timestamp = row['timestamp']
        o = row['open']
        h = row['high']
        l = row['low']
        c = row['close']
        v = row['volume']

        # Create two 30-second candles from one 1-minute candle
        # First 30s: open to midpoint
        mid_price = (o + h + l + c) / 4  # Simple approximation

        candles_30s.append({
            'timestamp': timestamp,
            'open': o,
            'high': max(h, mid_price),
            'low': min(l, mid_price),
            'close': mid_price,
            'volume': v // 2
        })

        # Second 30s: midpoint to close
        second_timestamp = timestamp + pd.Timedelta(seconds=30)

        candles_30s.append({
            'timestamp': second_timestamp,
            'open': mid_price,
            'high': max(h, mid_price),
            'low': min(l, mid_price),
            'close': c,
            'volume': v // 2
        })

    return candles_30s

if __name__ == '__main__':
    app.run(debug=True, port=5001)