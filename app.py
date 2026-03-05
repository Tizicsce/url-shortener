import os
import time
import requests
import json
import hashlib
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, jsonify, render_template_string

app = Flask(__name__)
DATABASE = 'urls.db'

# Telegram Config
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_WEBHOOK = os.getenv('TELEGRAM_WEBHOOK', '')
BOT_USERNAME = 'Shortener2_bot'

# ========== DATABASE FUNCTIONS ==========

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0,
            last_click TIMESTAMP,
            user_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def generate_short_code(url, user_id=''):
    """Generate short code"""
    hash_object = hashlib.md5((url + user_id + str(datetime.now())).encode())
    return hash_object.hexdigest()[:6]

# ========== TELEGRAM BOT FUNCTIONS ==========

def send_telegram_message(chat_id, text, buttons=None):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if buttons:
            payload['reply_markup'] = json.dumps(buttons)
        
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def handle_telegram_update(update):
    """Handle Telegram update"""
    if 'message' not in update:
        return
    
    message = update['message']
    chat_id = message['chat']['id']
    text = message.get('text', '')
    user_id = str(message['from']['id'])
    
    # Get base URL from webhook or use default
    base_url = TELEGRAM_WEBHOOK.replace('/webhook', '') if TELEGRAM_WEBHOOK else 'https://web-production-5abe3.up.railway.app'
    
    # Start command
    if text == '/start':
        welcome = """👋 <b>Welcome to URL Shortener Bot!</b>

🚀 <b>Commands:</b>
• Send me any URL to shorten
• /stats - Your statistics
• /help - Show help

💡 <b>Example:</b>
Just send: https://google.com

🌐 <b>Web App:</b>
Also available at our website!"""
        
        send_telegram_message(chat_id, welcome)
        return
    
    # Stats command
    if text == '/stats':
        conn = get_db_connection()
        total = conn.execute('SELECT COUNT(*) as count FROM urls WHERE user_id = ?', (user_id,)).fetchone()['count']
        total_clicks = conn.execute('SELECT SUM(clicks) as sum FROM urls WHERE user_id = ?', (user_id,)).fetchone()['sum'] or 0
        conn.close()
        
        stats = f"""📊 <b>Your Statistics</b>

🔗 URLs created: {total}
👆 Total clicks: {total_clicks}

💡 Send a URL to create a new short link!"""
        
        send_telegram_message(chat_id, stats)
        return
    
    # Help command
    if text == '/help':
        help_text = """❓ <b>How to use:</b>

1️⃣ Send me any long URL
2️⃣ I'll create a short link instantly
3️⃣ Share your short link anywhere!

<b>Commands:</b>
• /start - Welcome message
• /stats - Your statistics  
• /help - This help message

<b>Tip:</b>
You can also use our web interface!

Just paste any URL starting with http:// or https://"""
        
        send_telegram_message(chat_id, help_text)
        return
    
    # URL shortening
    if text.startswith('http'):
        # Validate URL
        if not text.startswith(('http://', 'https://')):
            text = 'https://' + text
        
        # Generate short code
        short_code = generate_short_code(text, user_id)
        
        # Save to database
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO urls (short_code, original_url, user_id) VALUES (?, ?, ?)',
                (short_code, text, user_id)
            )
            conn.commit()
            
            # Get short URL
            short_url = f"{base_url}/{short_code}"
            
            # Send success message with buttons
            buttons = {
                'inline_keyboard': [
                    [{'text': '🔗 Open Link', 'url': short_url}],
                    [{'text': '📊 View Stats', 'url': f'{host}api/stats/{short_code}'}]
                ]
            }
            
            response = f"""✅ <b>URL Shortened Successfully!</b>

🔗 <b>Short URL:</b>
<code>{short_url}</code>

🌐 <b>Original:</b>
{text[:60]}...

💡 Click the button below to open your link!"""
            
            send_telegram_message(chat_id, response, buttons)
            
        except sqlite3.IntegrityError:
            # URL already exists
            existing = conn.execute('SELECT short_code FROM urls WHERE original_url = ?', (text,)).fetchone()
            if existing:
                short_url = f"{base_url}/{existing['short_code']}"
                
                response = f"""ℹ️ <b>This URL is already shortened!</b>

🔗 <b>Short URL:</b>
<code>{short_url}</code>

💡 Your link is ready to use!"""
                send_telegram_message(chat_id, response)
        finally:
            conn.close()
        return
    
    # Unknown message
    send_telegram_message(chat_id, "❓ Please send me a valid URL starting with http:// or https://\n\nOr use /help for more information.")

# ========== FLASK ROUTES ==========

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔗 URL Shortener</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            width: 100%;
            text-align: center;
        }
        h1 { color: #333; margin-bottom: 10px; font-size: 2.5em; }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 1.1em; }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="url"] {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="url"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .result {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
            display: none;
        }
        .result.show { display: block; }
        .short-url {
            font-size: 20px;
            color: #667eea;
            font-weight: bold;
            word-break: break-all;
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 8px;
        }
        .telegram-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 25px;
            padding: 14px 28px;
            background: #0088cc;
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: background 0.3s;
        }
        .telegram-btn:hover { background: #006699; }
        .features {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #e0e0e0;
        }
        .feature {
            text-align: center;
        }
        .feature-icon {
            font-size: 2em;
            margin-bottom: 5px;
        }
        .feature-text {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URL Shortener</h1>
        <p class="subtitle">Shorten your links instantly!<br>Available on Web & Telegram</p>
        
        <form id="shortenForm">
            <div class="input-group">
                <input type="url" id="urlInput" placeholder="Paste your long URL here..." required>
                <button type="submit">Shorten</button>
            </div>
        </form>
        
        <div id="result" class="result">
            <p>✅ Your shortened URL:</p>
            <div class="short-url" id="shortUrl"></div>
            <button onclick="copyUrl()" style="margin-top: 10px;">📋 Copy</button>
        </div>
        
        <a href="https://t.me/Shortener2_bot" class="telegram-btn" target="_blank">
            🤖 Open Telegram Bot
        </a>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">⚡</div>
                <div class="feature-text">Instant</div>
            </div>
            <div class="feature">
                <div class="feature-icon">📊</div>
                <div class="feature-text">Analytics</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🆓</div>
                <div class="feature-text">Free</div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('shortenForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('urlInput').value;
            
            const response = await fetch('/api/shorten', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url})
            });
            
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('result').classList.add('show');
                document.getElementById('shortUrl').textContent = data.short_url;
            }
        });
        
        function copyUrl() {
            const url = document.getElementById('shortUrl').textContent;
            navigator.clipboard.writeText(url).then(() => {
                alert('Copied to clipboard!');
            });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Home page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    """API endpoint to shorten URL"""
    data = request.get_json()
    original_url = data.get('url')
    
    if not original_url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
    
    if not original_url.startswith(('http://', 'https://')):
        original_url = 'https://' + original_url
    
    short_code = generate_short_code(original_url)
    
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO urls (short_code, original_url) VALUES (?, ?)',
            (short_code, original_url)
        )
        conn.commit()
        short_url = request.host_url + short_code
        return jsonify({'success': True, 'short_url': short_url})
    except sqlite3.IntegrityError:
        existing = conn.execute('SELECT short_code FROM urls WHERE original_url = ?', (original_url,)).fetchone()
        if existing:
            return jsonify({'success': True, 'short_url': request.host_url + existing['short_code']})
        return jsonify({'success': False, 'error': 'Failed to create short URL'}), 500
    finally:
        conn.close()

@app.route('/<short_code>')
def redirect_to_url(short_code):
    """Redirect short URL"""
    conn = get_db_connection()
    url = conn.execute('SELECT * FROM urls WHERE short_code = ?', (short_code,)).fetchone()
    
    if url:
        conn.execute('UPDATE urls SET clicks = clicks + 1, last_click = ? WHERE short_code = ?',
                    (datetime.now(), short_code))
        conn.commit()
        conn.close()
        return redirect(url['original_url'])
    
    conn.close()
    return "URL not found", 404

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Telegram webhook endpoint"""
    update = request.get_json()
    handle_telegram_update(update)
    return jsonify({'status': 'ok'})

@app.route('/api/stats/<short_code>')
def get_stats(short_code):
    """Get URL stats"""
    conn = get_db_connection()
    url = conn.execute('SELECT * FROM urls WHERE short_code = ?', (short_code,)).fetchone()
    conn.close()
    
    if url:
        return jsonify({
            'short_code': url['short_code'],
            'original_url': url['original_url'],
            'clicks': url['clicks'],
            'created_at': url['created_at'],
            'last_click': url['last_click']
        })
    return jsonify({'error': 'URL not found'}), 404

def set_telegram_webhook():
    """Set Telegram webhook on startup"""
    if TELEGRAM_TOKEN and TELEGRAM_WEBHOOK:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
            payload = {
                'url': TELEGRAM_WEBHOOK,
                'drop_pending_updates': True
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.json().get('ok'):
                print("✅ Telegram webhook configured successfully")
            else:
                print(f"⚠️ Webhook setup: {response.json()}")
        except Exception as e:
            print(f"⚠️ Webhook error: {e}")
    else:
        print("ℹ️ No Telegram token or webhook URL provided")

if __name__ == '__main__':
    init_db()
    set_telegram_webhook()
    
    # Run Flask
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
