# Deployment Requirements

## Files Needed

### 1. Update requirements.txt
Add gunicorn for production:
```
Flask==3.0.0
pdfplumber==0.10.3
python-docx==1.1.0
gunicorn==21.2.0
```

### 2. Create Procfile (for Railway/Render)
```
web: gunicorn app:app
```

### 3. Update app.py (change last line)
Replace:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

With:
```python
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
```

## Deployment Steps

### Option A: Google Cloud Run (I can deploy for you!)
Just say "Deploy to Cloud Run" and I'll handle it.

### Option B: Railway (Manual)
1. Go to railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repo
5. Railway auto-detects Flask and deploys

### Option C: Render (Manual)
1. Go to render.com
2. Sign up
3. Click "New" → "Web Service"
4. Connect GitHub repo
5. Render auto-deploys

## Which do you prefer?
I can automatically deploy to Google Cloud Run for you right now, or you can manually deploy to Railway/Render (both are very simple).
