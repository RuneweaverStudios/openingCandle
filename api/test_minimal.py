from flask import Flask, jsonify

app = Flask(__name__)

# Vercel serverless handler
def handler(environ, start_response):
    return app(environ, start_response)

@app.route('/')
def home():
    return "Hello World - Serverless Test"

@app.route('/test')
def test():
    return jsonify({"message": "Test endpoint working", "status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5001)