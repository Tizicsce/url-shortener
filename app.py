from flask import Flask, request, redirect, jsonify, render_template_string
import hashlib
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DATABASE = 'urls.db'

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
            last_click TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def generate_short_code(url):
    """Generate short code from URL"""
    # Use first 6 characters of MD5 hash
    hash_object = hashlib.md5(url.encode())
    return hash_object.hexdigest()[:6]

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# HTML Template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>URL Shortener</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
            max-width: 600px;
            width: 100%;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
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
        .result.show {
            display: block;
        }
        .short-url {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 10px;
        }
        .short-url a {
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
            font-size: 18px;
        }
        .copy-btn {
            padding: 8px 15px;
            font-size: 14px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #e0e0e0;
        }
        .stat-card {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
        }
        .url-list {
            margin-top: 30px;
            max-height: 300px;
            overflow-y: auto;
        }
        .url-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        .url-info {
            flex: 1;
            overflow: hidden;
        }
        .url-short {
            color: #667eea;
            font-weight: bold;
        }
        .url-original {
            color: #666;
            font-size: 12px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .url-clicks {
            background: #667eea;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URL Shortener</h1>
        <p class="subtitle">Shorten your links and track clicks</p>
        
        <form id="shortenForm">
            <div class="input-group">
                <input type="url" id="urlInput" placeholder="Enter your long URL here..." required>
                <button type="submit">Shorten</button>
            </div>
        </form>
        
        <div id="result" class="result">
            <p>✅ Your shortened URL:</p>
            <div class="short-url">
                <a id="shortLink" href="#" target="_blank"></a>
                <button class="copy-btn" onclick="copyUrl()">Copy</button>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ total_urls }}</div>
                <div class="stat-label">URLs</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_clicks }}</div>
                <div class="stat-label">Clicks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ avg_clicks }}</div>
                <div class="stat-label">Avg Clicks</div>
            </div>
        </div>
        
        {% if recent_urls %}
        <div class="url-list">
            <h3 style="margin-bottom: 15px;">Recent URLs</h3>
            {% for url in recent_urls %}
            <div class="url-item">
                <div class="url-info">
                    <div class="url-short">{{ request.host_url }}{{ url.short_code }}</div>
                    <div class="url-original">{{ url.original_url }}</div>
                </div>
                <div class="url-clicks">{{ url.clicks }} clicks</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
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
                const resultDiv = document.getElementById('result');
                const shortLink = document.getElementById('shortLink');
                shortLink.href = data.short_url;
                shortLink.textContent = data.short_url;
                resultDiv.classList.add('show');
            }
        });
        
        function copyUrl() {
            const link = document.getElementById('shortLink').textContent;
            navigator.clipboard.writeText(link);
            alert('Copied to clipboard!');
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Home page"""
    conn = get_db_connection()
    
    # Get stats
    total_urls = conn.execute('SELECT COUNT(*) as count FROM urls').fetchone()['count']
    total_clicks = conn.execute('SELECT SUM(clicks) as sum FROM urls').fetchone()['sum'] or 0
    avg_clicks = round(total_clicks / total_urls, 1) if total_urls > 0 else 0
    
    # Get recent URLs
    recent_urls = conn.execute(
        'SELECT * FROM urls ORDER BY created_at DESC LIMIT 5'
    ).fetchall()
    
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, 
                                  total_urls=total_urls,
                                  total_clicks=total_clicks,
                                  avg_clicks=avg_clicks,
                                  recent_urls=recent_urls)

@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    """API endpoint to shorten URL"""
    data = request.get_json()
    original_url = data.get('url')
    
    if not original_url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
    
    # Add http:// if not present
    if not original_url.startswith(('http://', 'https://')):
        original_url = 'https://' + original_url
    
    # Generate short code
    short_code = generate_short_code(original_url + str(datetime.now()))
    
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO urls (short_code, original_url) VALUES (?, ?)',
            (short_code, original_url)
        )
        conn.commit()
        
        short_url = request.host_url + short_code
        return jsonify({
            'success': True,
            'short_url': short_url,
            'short_code': short_code
        })
    except sqlite3.IntegrityError:
        # If code exists, get existing one
        existing = conn.execute(
            'SELECT short_code FROM urls WHERE original_url = ?',
            (original_url,)
        ).fetchone()
        if existing:
            return jsonify({
                'success': True,
                'short_url': request.host_url + existing['short_code'],
                'short_code': existing['short_code']
            })
        return jsonify({'success': False, 'error': 'Failed to create short URL'}), 500
    finally:
        conn.close()

@app.route('/<short_code>')
def redirect_to_url(short_code):
    """Redirect short URL to original"""
    conn = get_db_connection()
    url = conn.execute(
        'SELECT * FROM urls WHERE short_code = ?',
        (short_code,)
    ).fetchone()
    
    if url:
        # Update click stats
        conn.execute(
            'UPDATE urls SET clicks = clicks + 1, last_click = ? WHERE short_code = ?',
            (datetime.now(), short_code)
        )
        conn.commit()
        conn.close()
        return redirect(url['original_url'])
    
    conn.close()
    return "URL not found", 404

@app.route('/api/stats/<short_code>')
def get_stats(short_code):
    """Get stats for a short URL"""
    conn = get_db_connection()
    url = conn.execute(
        'SELECT * FROM urls WHERE short_code = ?',
        (short_code,)
    ).fetchone()
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

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
