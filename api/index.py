from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import sys
import traceback

app = Flask(__name__)

# Standard Vercel serverless handler with error handling
def handler(environ, start_response):
    """Vercel serverless function handler"""
    try:
        return app(environ, start_response)
    except Exception as e:
        # Log the full error for debugging
        error_msg = f"Handler error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)

        # Return a 500 error response
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'application/json')]
        start_response(status, headers)
        error_response = jsonify({
            'error': 'Internal server error',
            'details': str(e)
        })
        return [error_response.data]

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'message': 'API is working'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/mnq-data', methods=['GET'])
def get_mnq_data():
    """Fetch MNQ futures data from Yahoo Finance"""
    try:
        date = request.args.get('date')

        pacific = pytz.timezone('America/Los_Angeles')
        if date:
            try:
                target_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400
        else:
            target_date = datetime.now(pacific).date()
            if target_date.weekday() >= 5:
                target_date = target_date - timedelta(days=target_date.weekday() - 4)
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
            return jsonify({'error': 'No data found for this date. Yahoo Finance typically only provides intraday data for the last 7 days.'}), 404

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
    if minutes == 0.5:
        return create_30second_data(df)

    if minutes == 1:
        return df.to_dict('records')

    df_temp = df.set_index('timestamp')
    df_resampled = df_temp.resample(f'{minutes}min').agg({
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

        mid_price = (o + h + l + c) / 4

        candles_30s.append({
            'timestamp': timestamp.isoformat(),
            'open': float(o),
            'high': float(max(h, mid_price)),
            'low': float(min(l, mid_price)),
            'close': float(mid_price),
            'volume': int(v // 2)
        })

        second_timestamp = timestamp + pd.Timedelta(seconds=30)

        candles_30s.append({
            'timestamp': second_timestamp.isoformat(),
            'open': float(mid_price),
            'high': float(max(h, mid_price)),
            'low': float(min(l, mid_price)),
            'close': float(c),
            'volume': int(v // 2)
        })

    return candles_30s

# Add this for local testing
if __name__ == '__main__':
    app.run(debug=True, port=5001)