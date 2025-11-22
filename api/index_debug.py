from flask import Flask, jsonify

app = Flask(__name__)

# Vercel serverless handler
def handler(environ, start_response):
    return app(environ, start_response)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Debug Test</title></head>
    <body>
        <h1>Debug Test - Flask Working</h1>
        <p>If you can see this, Flask is working on Vercel.</p>
    </body>
    </html>
    '''

@app.route('/api/test')
def test():
    return jsonify({"status": "working", "message": "Basic Flask API working"})

if __name__ == '__main__':
    app.run(debug=True, port=5001)