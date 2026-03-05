# URL Shortener 🔗

A simple, beautiful URL shortener with click tracking.

## Features ✨

- ✅ Shorten any URL
- 📊 Track click statistics
- 💾 SQLite database
- 🎨 Beautiful web interface
- 📱 Mobile responsive
- 🔗 API endpoint

## Installation 🚀

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

## Usage 💡

### Web Interface
Open `http://localhost:5000` in your browser

### API
```bash
curl -X POST http://localhost:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Response:
```json
{
  "success": true,
  "short_url": "http://localhost:5000/a3f5d2",
  "short_code": "a3f5d2"
}
```

### Get Stats
```bash
curl http://localhost:5000/api/stats/a3f5d2
```

## Deployment 🌐

### Railway (Free)
1. Push to GitHub
2. Connect Railway to your repo
3. Deploy automatically

### PythonAnywhere (Free)
1. Upload files
2. Set up Flask app
3. Run!

## Database 📊

Uses SQLite with fields:
- `short_code` - Unique code (6 chars)
- `original_url` - Full URL
- `created_at` - Creation date
- `clicks` - Click count
- `last_click` - Last click timestamp
