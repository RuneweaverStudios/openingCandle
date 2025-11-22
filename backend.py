from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["null", "file://", "*"]}})  # Enable CORS for all origins including file://

@app.route('/')
def serve_index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)

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
        print(f"DEBUG: Raw data shape: {df.shape}")
        print(f"DEBUG: Raw data columns: {df.columns.tolist()}")

        thirty_sec_data = process_timeframe(df, 0.5)
        five_min_data = process_timeframe(df, 5)
        fifteen_min_data = process_timeframe(df, 15)

        print(f"DEBUG: 30s data length: {len(thirty_sec_data)}")
        print(f"DEBUG: 5m data length: {len(five_min_data)}")
        print(f"DEBUG: 15m data length: {len(fifteen_min_data)}")

        if thirty_sec_data:
            print(f"DEBUG: First 30s candle: {thirty_sec_data[0]}")

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