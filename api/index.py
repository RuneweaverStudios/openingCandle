import json

def handler(request):
    """Vercel serverless function without Flask"""

    # Get the path from the request
    path = request.get('path', '')
    method = request.get('method', 'GET')

    if path == '/api/test':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'success',
                'message': 'Serverless function is working!',
                'method': method,
                'path': path
            })
        }

    elif path == '/api/mnq-data':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'date': '2024-11-21',
                'status': 'mock_data',
                'message': 'Real yfinance integration temporarily disabled for testing',
                'data': {
                    '30s': [],
                    '5m': [],
                    '15m': []
                }
            })
        }

    else:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Not found',
                'path': path
            })
        }