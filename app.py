"""
GEMMAHUB - SaaS Platform
Users bring their own Groq API key
"""

from flask import Flask, render_template, request, jsonify, make_response
import requests
import re
import os

app = Flask(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

def clean_text(text):
    if not text:
        return "I'm here! Ask me anything."
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`{3}[\s\S]*?`{3}', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    if len(text.strip()) < 3:
        return "I'm thinking... Please try again."
    return text.strip()

@app.route('/')
def index():
    html = render_template('index.html')
    response = make_response(html)
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({'error': 'no_api_key', 'message': 'Please add your Groq API key in settings.'})
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        groq_messages = [
            {
                "role": "system",
                "content": """You are Gemma, a helpful AI assistant powered by Google.

RULES:
- Answer naturally in conversational style
- Be helpful, friendly and informative
- No markdown formatting like **bold** or *italics*
- Use plain paragraphs"""
            }
        ]
        
        for msg in messages[-10:]:
            groq_messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        payload = {
            "model": MODEL,
            "messages": groq_messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 401:
            return jsonify({'error': 'invalid_key', 'message': 'Invalid API key. Please check your Groq API key.'})
        elif response.status_code == 429:
            return jsonify({'error': 'rate_limit', 'message': 'Rate limit reached. Please wait a moment.'})
        elif response.status_code != 200:
            return jsonify({'error': 'api_error', 'message': 'API error. Please try again.'})
        
        result = response.json()
        answer = clean_text(result['choices'][0]['message']['content'])
        return jsonify({'response': answer})
    
    except requests.exceptions.Timeout:
        return jsonify({'error': 'timeout', 'message': 'Request timed out. Please try again.'})
    except Exception as e:
        return jsonify({'error': 'error', 'message': 'Something went wrong. Please try again.'})

@app.route('/api/verify-key', methods=['POST'])
def verify_key():
    data = request.json
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({'valid': False, 'message': 'No API key provided'})
    
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"model": MODEL, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            return jsonify({'valid': True})
        else:
            return jsonify({'valid': False, 'message': 'Invalid API key'})
    except:
        return jsonify({'valid': False, 'message': 'Could not verify key'})

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({'status': 'online', 'model': MODEL})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
