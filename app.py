
import os
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

from agent_instructions import build_system_prompt, RAG_SETTINGS, AGENT_NAME
from recipe_data import rag_engine, RECIPES

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")
CORS(app)

# ---------------------------------------------------------------------------
# Gemini Configuration
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY not found. Create a .env file with your key. "
        "See .env.example for the template."
    )

genai.configure(api_key=GEMINI_API_KEY)

# Generation config — tuned for culinary responses
GENERATION_CONFIG = genai.types.GenerationConfig(
    temperature=0.8,
    top_p=0.95,
    top_k=40,
    max_output_tokens=2048,
)

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT",       "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

MAX_CHAT_HISTORY = int(os.getenv("MAX_CHAT_HISTORY", 20))

# In-memory session store (use Redis for production)
_sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_session(session_id: str) -> dict:
    """Return existing session data or initialise a new one."""
    if session_id not in _sessions:
        _sessions[session_id] = {
            "history": [],
            "dietary_prefs": [],
            "allergies": [],
            "saved_recipes": [],
            "current_ingredients": [],
            "created_at": datetime.utcnow().isoformat(),
        }
    return _sessions[session_id]


def _build_gemini_model(session_data: dict) -> genai.GenerativeModel:
    """Construct a Gemini model with the current session's system prompt."""
    system_prompt = build_system_prompt(
        user_dietary_prefs=session_data.get("dietary_prefs", []),
        user_allergies=session_data.get("allergies", []),
    )
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=GENERATION_CONFIG,
        safety_settings=SAFETY_SETTINGS,
        system_instruction=system_prompt,
    )


def _trim_history(history: list) -> list:
    """Keep only the last MAX_CHAT_HISTORY turns."""
    return history[-MAX_CHAT_HISTORY:] if len(history) > MAX_CHAT_HISTORY else history


def _history_to_gemini_format(history: list) -> list:
    """Convert internal history format to Gemini API format."""
    gemini_history = []
    for turn in history:
        gemini_history.append({"role": turn["role"], "parts": [turn["content"]]})
    return gemini_history


def _extract_preferences_from_message(message: str, session_data: dict):
    """
    Lightweight heuristic to detect dietary preferences or allergies
    mentioned inline by the user (avoids a round-trip to Gemini).
    """
    msg_lower = message.lower()
    diet_keywords = {
        "vegan": "Vegan", "vegetarian": "Vegetarian",
        "gluten-free": "Gluten-Free", "gluten free": "Gluten-Free",
        "dairy-free": "Dairy-Free", "dairy free": "Dairy-Free",
        "keto": "Keto", "paleo": "Paleo", "halal": "Halal",
        "kosher": "Kosher", "low-carb": "Low-Carb", "low carb": "Low-Carb",
    }
    allergy_keywords = {
        "allergic to nuts": "Tree Nuts", "nut allergy": "Tree Nuts",
        "peanut allergy": "Peanuts", "shellfish allergy": "Shellfish",
        "lactose intolerant": "Dairy", "allergic to gluten": "Wheat",
        "egg allergy": "Eggs", "soy allergy": "Soy",
    }
    for kw, label in diet_keywords.items():
        if kw in msg_lower and label not in session_data["dietary_prefs"]:
            session_data["dietary_prefs"].append(label)
    for kw, label in allergy_keywords.items():
        if kw in msg_lower and label not in session_data["allergies"]:
            session_data["allergies"].append(label)


# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", agent_name=AGENT_NAME)


# ---------------------------------------------------------------------------
# Routes — Chat API
# ---------------------------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Accepts: { session_id, message, ingredients (optional) }
    Returns:  { reply, retrieved_recipes, session_id, timestamp }
    """
    try:
        data = request.get_json(force=True)
        session_id  = data.get("session_id") or f"sess_{int(time.time()*1000)}"
        user_message = data.get("message", "").strip()
        ingredients  = data.get("ingredients", [])

        if not user_message:
            return jsonify({"error": "Message cannot be empty."}), 400

        session_data = _get_or_create_session(session_id)
        _extract_preferences_from_message(user_message, session_data)

        # If ingredients are passed, merge them and fold into message
        if ingredients:
            session_data["current_ingredients"] = list(
                set(session_data["current_ingredients"] + [i.strip() for i in ingredients if i.strip()])
            )

        # ------------------------------------------------------------------
        # RAG: Retrieve relevant recipes
        # ------------------------------------------------------------------
        rag_query = user_message
        if session_data["current_ingredients"]:
            rag_query += " " + " ".join(session_data["current_ingredients"])

        retrieved = rag_engine.retrieve(rag_query, top_k=RAG_SETTINGS["top_k"])
        rag_context = rag_engine.format_for_context(retrieved)

        # ------------------------------------------------------------------
        # Build the augmented user message
        # ------------------------------------------------------------------
        if session_data["current_ingredients"]:
            ingredients_note = (
                f"\n\n[USER'S AVAILABLE INGREDIENTS: "
                f"{', '.join(session_data['current_ingredients'])}]"
            )
        else:
            ingredients_note = ""

        augmented_message = (
            f"{rag_context}\n\n"
            f"USER MESSAGE: {user_message}"
            f"{ingredients_note}"
        )

        # ------------------------------------------------------------------
        # Call Gemini
        # ------------------------------------------------------------------
        model = _build_gemini_model(session_data)
        chat_obj = model.start_chat(
            history=_history_to_gemini_format(
                _trim_history(session_data["history"])
            )
        )
        response = chat_obj.send_message(augmented_message)
        reply_text = response.text

        # ------------------------------------------------------------------
        # Persist history (store original user message, not augmented)
        # ------------------------------------------------------------------
        session_data["history"].append({"role": "user",  "content": user_message})
        session_data["history"].append({"role": "model", "content": reply_text})

        # ------------------------------------------------------------------
        # Build response payload
        # ------------------------------------------------------------------
        retrieved_summary = [
            {
                "id": r["id"],
                "name": r["name"],
                "cuisine": r["cuisine"],
                "difficulty": r["difficulty"],
                "prep_time": r["prep_time"],
                "cook_time": r["cook_time"],
                "servings": r["servings"],
                "diet_tags": r["diet_tags"],
                "allergens": r["allergens"],
                "description": r["description"],
                "score": round(score, 3),
            }
            for r, score in retrieved
        ]

        return jsonify({
            "session_id": session_id,
            "reply": reply_text,
            "retrieved_recipes": retrieved_summary,
            "timestamp": datetime.utcnow().isoformat(),
            "current_ingredients": session_data["current_ingredients"],
            "dietary_prefs": session_data["dietary_prefs"],
        })

    except genai.types.BlockedPromptException:
        return jsonify({"error": "Message was blocked by safety filters. Please rephrase."}), 400
    except Exception as exc:
        app.logger.exception("Chat error")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Routes — Recipe Search
# ---------------------------------------------------------------------------

@app.route("/api/recipes/search", methods=["GET"])
def search_recipes():
    """
    Search the recipe catalog.
    Query params: q (text), cuisine, diet, difficulty
    """
    query     = request.args.get("q", "").strip()
    cuisine   = request.args.get("cuisine", "").strip().lower()
    diet      = request.args.get("diet", "").strip().lower()
    difficulty= request.args.get("difficulty", "").strip().lower()

    if not query and not cuisine and not diet and not difficulty:
        return jsonify({"recipes": RECIPES})

    if query:
        results = [r for r, _ in rag_engine.retrieve(query, top_k=20, threshold=0.0)]
    else:
        results = RECIPES[:]

    # Apply filters
    if cuisine:
        results = [r for r in results if cuisine in r["cuisine"].lower()]
    if diet:
        results = [r for r in results if any(diet in tag for tag in r["diet_tags"])]
    if difficulty:
        results = [r for r in results if r["difficulty"].lower() == difficulty]

    return jsonify({"recipes": results, "count": len(results)})


@app.route("/api/recipes/<recipe_id>", methods=["GET"])
def get_recipe(recipe_id: str):
    """Retrieve a single recipe by ID."""
    recipe = rag_engine.get_recipe_by_id(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found."}), 404
    return jsonify(recipe)


# ---------------------------------------------------------------------------
# Routes — Ingredient Manager
# ---------------------------------------------------------------------------

@app.route("/api/ingredients", methods=["GET"])
def get_ingredients():
    session_id = request.args.get("session_id", "")
    session_data = _get_or_create_session(session_id)
    return jsonify({"ingredients": session_data["current_ingredients"]})


@app.route("/api/ingredients", methods=["POST"])
def update_ingredients():
    data = request.get_json(force=True)
    session_id  = data.get("session_id", "")
    ingredients = data.get("ingredients", [])
    session_data = _get_or_create_session(session_id)
    session_data["current_ingredients"] = [i.strip() for i in ingredients if i.strip()]
    return jsonify({
        "ingredients": session_data["current_ingredients"],
        "message": f"{len(session_data['current_ingredients'])} ingredient(s) saved."
    })


@app.route("/api/ingredients/<ingredient>", methods=["DELETE"])
def delete_ingredient(ingredient: str):
    session_id = request.args.get("session_id", "")
    session_data = _get_or_create_session(session_id)
    session_data["current_ingredients"] = [
        i for i in session_data["current_ingredients"]
        if i.lower() != ingredient.lower()
    ]
    return jsonify({"ingredients": session_data["current_ingredients"]})


# ---------------------------------------------------------------------------
# Routes — Session Management
# ---------------------------------------------------------------------------

@app.route("/api/session", methods=["GET"])
def get_session():
    session_id = request.args.get("session_id", "")
    if not session_id or session_id not in _sessions:
        return jsonify({"exists": False})
    data = _sessions[session_id]
    return jsonify({
        "exists": True,
        "session_id": session_id,
        "dietary_prefs": data["dietary_prefs"],
        "allergies": data["allergies"],
        "ingredients_count": len(data["current_ingredients"]),
        "history_count": len(data["history"]),
    })


@app.route("/api/session/preferences", methods=["POST"])
def update_preferences():
    data = request.get_json(force=True)
    session_id = data.get("session_id", "")
    session_data = _get_or_create_session(session_id)
    if "dietary_prefs" in data:
        session_data["dietary_prefs"] = data["dietary_prefs"]
    if "allergies" in data:
        session_data["allergies"] = data["allergies"]
    return jsonify({
        "dietary_prefs": session_data["dietary_prefs"],
        "allergies": session_data["allergies"],
    })


@app.route("/api/session/clear", methods=["POST"])
def clear_session():
    data = request.get_json(force=True)
    session_id = data.get("session_id", "")
    if session_id in _sessions:
        _sessions[session_id]["history"] = []
    return jsonify({"message": "Chat history cleared."})


# ---------------------------------------------------------------------------
# Routes — Quick Actions
# ---------------------------------------------------------------------------

@app.route("/api/quick-action", methods=["POST"])
def quick_action():
    """
    Predefined quick actions that call the chat endpoint internally.
    Actions: 'suggest_with_ingredients', 'random_recipe', 'cooking_tip'
    """
    data = request.get_json(force=True)
    action     = data.get("action", "")
    session_id = data.get("session_id", "")
    session_data = _get_or_create_session(session_id)

    action_messages = {
        "suggest_with_ingredients": (
            f"Based on the ingredients I have ({', '.join(session_data['current_ingredients']) or 'various pantry items'}), "
            "what recipes can I make? Give me your top 3 suggestions with brief descriptions."
        ),
        "random_recipe": "Surprise me with a random interesting recipe I should try today!",
        "cooking_tip":   "Give me one professional cooking tip I can apply right now to improve my cooking.",
        "substitutions": "What are the most useful ingredient substitutions I should know as a home cook?",
        "meal_plan":     "Suggest a simple 3-day meal plan (breakfast, lunch, dinner) using common ingredients.",
    }

    message = action_messages.get(action, data.get("message", ""))
    if not message:
        return jsonify({"error": "Unknown action."}), 400

    # Delegate to the chat endpoint logic (reuse without HTTP overhead)
    request._cached_json = {  # inject into request context for _chat logic
        "session_id": session_id,
        "message": message,
        "ingredients": session_data["current_ingredients"],
    }

    # Re-use chat logic directly
    rag_query = message
    if session_data["current_ingredients"]:
        rag_query += " " + " ".join(session_data["current_ingredients"])

    retrieved = rag_engine.retrieve(rag_query)
    rag_context = rag_engine.format_for_context(retrieved)

    augmented = f"{rag_context}\n\nUSER MESSAGE: {message}"

    model = _build_gemini_model(session_data)
    chat_obj = model.start_chat(history=_history_to_gemini_format(_trim_history(session_data["history"])))
    response = chat_obj.send_message(augmented)
    reply_text = response.text

    session_data["history"].append({"role": "user",  "content": message})
    session_data["history"].append({"role": "model", "content": reply_text})

    return jsonify({
        "session_id": session_id,
        "reply": reply_text,
        "action": action,
        "timestamp": datetime.utcnow().isoformat(),
    })


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "agent": AGENT_NAME,
        "model": "gemini-2.5-flash",
        "recipes_in_db": len(RECIPES),
        "timestamp": datetime.utcnow().isoformat(),
    })


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    print(f"\n{'='*60}")
    print(f"  🍳  {AGENT_NAME} — AI Recipe Preparation Agent")
    print(f"  🌐  Running on http://localhost:{port}")
    print(f"  📚  {len(RECIPES)} recipes in knowledge base")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
