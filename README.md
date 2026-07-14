# 🍳 AI Recipe Preparation Agent

An AI-powered recipe assistant built with **Python Flask** and **Google Gemini 2.5 Flash**. Features a modern chat UI, recipe dashboard, pantry manager, semantic recipe search (RAG), and a fully customizable AI agent persona.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Chat** | Conversational cooking assistant powered by Gemini 2.5 Flash |
| 📚 **RAG Recipes** | TF-IDF semantic retrieval injects relevant recipes into every prompt |
| 🧺 **Pantry Manager** | Track ingredients you have on hand for personalized suggestions |
| 🔍 **Recipe Search** | Filter by cuisine, diet, difficulty; semantic keyword search |
| 🥦 **Dietary Awareness** | Persistent diet preferences and allergy hard-constraints |
| 🔄 **Substitutions** | AI-powered ingredient substitution with ratio explanations |
| 🌙 **Dark Mode** | Full light/dark theme with localStorage persistence |
| 📱 **Responsive** | Mobile-first design with Bootstrap 5 |
| 🎛️ **Agent Instructions** | Single file to customize AI persona, cuisine focus, tone, safety |

---

## 🗂️ Project Structure

```
recipe_agent/
├── app.py                  # Flask application — all API routes
├── agent_instructions.py   # ⭐ Customize agent behavior HERE
├── recipe_data.py          # RAG knowledge base + retrieval engine
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .env                    # Your secrets (never commit this!)
├── templates/
│   └── index.html          # Single-page HTML application
└── static/
    ├── css/
    │   └── style.css       # Complete custom stylesheet
    └── js/
        └── app.js          # Frontend JavaScript
```

---

## 🚀 Quick Start (Local)

### 1. Prerequisites

- Python 3.10 or higher
- A Google Gemini API key → [Get one here](https://aistudio.google.com/app/apikey)

### 2. Clone / Navigate

```bash
cd recipe_agent
```

### 3. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy the template
cp .env.example .env

# Edit .env and set your values:
# GEMINI_API_KEY=AIza...your_key_here
# FLASK_SECRET_KEY=some-random-string-here
```

### 6. Run the Application

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🎛️ Customizing the Agent

All agent behavior is controlled from a **single file**: `agent_instructions.py`

### Change the Agent's Name & Personality

```python
# agent_instructions.py

AGENT_NAME = "Chef Marco"          # Change the agent's name

AGENT_PERSONALITY = """
You are Chef Marco, a strict Italian traditionalist who insists on
authentic techniques. You are passionate, opinionated, and occasionally
dramatic when someone suggests putting pineapple on pizza.
"""
```

### Specialize in a Cuisine

```python
PRIMARY_CUISINES = ["Italian", "French"]  # Focus on specific cuisines

CUISINE_PHILOSOPHY = """
You specialize exclusively in Italian and French cuisine. For other
cuisine requests, you provide general guidance but recommend consulting
regional specialists.
"""
```

### Set Dietary Defaults

```python
DEFAULT_DIETARY_NOTE = """
Always suggest a vegan alternative for every recipe by default.
"""
```

### Customize Substitution Rules

```python
SUBSTITUTION_RULES = """
Always prioritize budget-friendly substitutions available in
a typical American grocery store under $5.
"""
```

### Adjust Safety Rules

```python
SAFETY_RULES = """
...add your custom safety policies here...
"""
```

### Tune RAG Retrieval

```python
RAG_SETTINGS = {
    "top_k": 8,                    # Return more recipes per query
    "similarity_threshold": 0.15,  # Lower = more permissive matching
    "max_context_recipes": 5,      # More context for complex queries
}
```

---

## 📖 Adding Recipes to the Knowledge Base

Edit the `RECIPES` list in `recipe_data.py`:

```python
RECIPES = [
    # ... existing recipes ...
    {
        "id":          "r013",                   # Unique ID
        "name":        "My Custom Recipe",
        "cuisine":     "American",
        "diet_tags":   ["vegan", "gluten-free"], # See supported tags
        "allergens":   ["soy"],                  # Top-9 allergens
        "prep_time":   "15 min",
        "cook_time":   "30 min",
        "servings":    4,
        "difficulty":  "Easy",                   # Easy / Medium / Hard
        "ingredients": ["ingredient 1", "ingredient 2"],
        "instructions":["Step 1...", "Step 2..."],
        "tips":        ["Pro tip 1", "Pro tip 2"],
        "description": "A brief, appetizing description.",
    },
]
```

The RAG engine re-indexes automatically on startup — no rebuild required.

---

## 🌐 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Main application |
| `POST` | `/api/chat` | Chat with the AI agent |
| `GET`  | `/api/recipes/search` | Search recipes (`?q=&cuisine=&diet=&difficulty=`) |
| `GET`  | `/api/recipes/<id>` | Get recipe by ID |
| `GET`  | `/api/ingredients` | Get session pantry |
| `POST` | `/api/ingredients` | Update session pantry |
| `DELETE`| `/api/ingredients/<name>` | Remove ingredient |
| `POST` | `/api/quick-action` | Trigger quick actions |
| `POST` | `/api/session/preferences` | Update dietary preferences |
| `POST` | `/api/session/clear` | Clear chat history |
| `GET`  | `/api/health` | Health check |

### Chat Request Example

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session",
    "message": "What can I make with chicken and lemon?",
    "ingredients": ["chicken breast", "lemon", "garlic", "butter"]
  }'
```

---

## ☁️ Deployment

### Option A — Render (Free Tier)

1. Push your project to GitHub (ensure `.env` is in `.gitignore`).
2. Go to [render.com](https://render.com) → **New Web Service**.
3. Connect your GitHub repo.
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
6. Add **Environment Variables** in the Render dashboard:
   - `GEMINI_API_KEY` = your key
   - `FLASK_SECRET_KEY` = random secret
### Option B — Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up

# Set secrets
railway variables set GEMINI_API_KEY=your_key FLASK_SECRET_KEY=your_secret
```

### Option C — Heroku

```bash
# Login
heroku login

# Create app
heroku create my-recipe-agent

# Set config vars
heroku config:set GEMINI_API_KEY=your_key FLASK_SECRET_KEY=your_secret

# Deploy
git push heroku main
```

### Option D — Docker

```dockerfile
# Dockerfile (create in recipe_agent/)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2"]
```

```bash
docker build -t recipe-agent .
docker run -p 5000:5000 --env-file .env recipe-agent
```

---

## 🔒 Security Notes

- **Never commit `.env`** — it contains your API key. Add it to `.gitignore`.
- Set a strong `FLASK_SECRET_KEY` in production.
- The in-memory session store (`_sessions` dict in `app.py`) resets on restart. For production, replace with **Redis** (`flask-session` + `redis-py`).
- Consider rate-limiting the `/api/chat` endpoint for public deployments.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `EnvironmentError: GEMINI_API_KEY not found` | Create `.env` file with your key |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `429 Resource Exhausted` from Gemini | You've hit the free-tier rate limit; wait 1 minute |
| Chat responses are cut off | Increase `max_output_tokens` in `GENERATION_CONFIG` in `app.py` |
| Dark mode not persisting | Clear localStorage: `localStorage.clear()` in browser console |

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `flask` | 3.0.3 | Web framework |
| `flask-cors` | 4.0.1 | Cross-origin request support |
| `google-generativeai` | 0.8.3 | Gemini AI SDK |
| `python-dotenv` | 1.0.1 | `.env` file support |
| `scikit-learn` | 1.5.1 | TF-IDF vectorizer for RAG |
| `numpy` | 1.26.4 | Vector operations |
| `gunicorn` | 22.0.0 | Production WSGI server |

---

## 📄 License

MIT — free to use, modify, and distribute.

---

*Built with Flask · Google Gemini 2.5 Flash · Bootstrap 5*
