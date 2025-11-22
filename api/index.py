import json
import sys
from flask import Flask, request

app = Flask(__name__)

# Simple test endpoint to verify the function works
@app.route('/api/test', methods=['GET'])
def test():
    """Simple test endpoint"""
    return json.dumps({
        'status': 'success',
        'message': 'Serverless function is working!',
        'method': request.method,
        'path': request.path
    })

@app.route('/api/mnq-data', methods=['GET'])
def get_mnq_data():
    """Simplified MNQ data endpoint"""
    try:
        # Return mock data for now to test the endpoint
        return json.dumps({
            'date': '2024-11-21',
            'status': 'mock_data',
            'message': 'Real yfinance integration temporarily disabled for testing',
            'data': {
                '30s': [],
                '5m': [],
                '15m': []
            }
        })
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'type': type(e).__name__
        }), 500

# Vercel serverless handler
def handler(environ, start_response):
    """Vercel serverless function handler"""
    return app(environ, start_response)

if __name__ == '__main__':
    app.run(debug=True, port=5001)