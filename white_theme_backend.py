#!/usr/bin/env python3
"""
White Theme Backend for MNQ Futures Charts
Separate backend to avoid template string conflicts
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for
import yfinance as yf
import datetime
import pandas as pd
import numpy as np
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def root():
    """Redirect root to white theme page"""
    return redirect(url_for('white_theme'))

@app.route('/white-theme')
def white_theme():
    """White theme version with clean template structure"""
    return render_template('white_theme.html')

@app.route('/api/mnq-data')
def get_data():
    """API endpoint that fetches data from main backend"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'error': 'Date parameter is required'})

        # Fetch data from main backend - FIXED: use correct endpoint
        import requests
        response = requests.get(f'http://127.0.0.1:5001/api/mnq-data?date={date_str}', timeout=30)

        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({'error': f'Backend error: {response.status_code}'}), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to connect to main backend: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/winrate')
def get_winrate_data():
    """API endpoint that fetches winrate data from main backend"""
    try:
        # Fetch winrate data from main backend
        import requests
        response = requests.get(f'http://127.0.0.1:5001/api/winrate', timeout=30)

        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({'error': f'Backend error: {response.status_code}'}), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to connect to main backend: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)