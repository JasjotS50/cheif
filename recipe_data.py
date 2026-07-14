# =============================================================================
#  RECIPE DATABASE — RAG Knowledge Base
#  Add, edit, or remove recipes here to expand the agent's curated knowledge.
# =============================================================================

# Pure-Python TF-IDF — no numpy or scikit-learn required.
import math
import re
from collections import Counter
from agent_instructions import RAG_SETTINGS

# ---------------------------------------------------------------------------
# RECIPE CATALOG
# Each recipe is a dict with standardised keys. Add your own recipes freely.
# ---------------------------------------------------------------------------
RECIPES = [
    {
        "id": "r001",
        "name": "Classic Spaghetti Carbonara",
        "cuisine": "Italian",
        "diet_tags": ["dairy-free-option"],
        "allergens": ["eggs", "wheat", "milk"],
        "prep_time": "10 min",
        "cook_time": "20 min",
        "servings": 4,
        "difficulty": "Medium",
        "ingredients": ["spaghetti", "eggs", "pancetta", "parmesan cheese", "black pepper", "salt", "garlic"],
        "instructions": [
            "Boil salted water and cook spaghetti al dente.",
            "Fry pancetta until crispy in a large pan.",
            "Whisk eggs with grated parmesan and plenty of black pepper.",
            "Reserve 1 cup pasta water before draining.",
            "Off heat, toss hot pasta with pancetta, then quickly stir in egg mixture.",
            "Add pasta water splash by splash until creamy. Serve immediately."
        ],
        "tips": ["Never add cream — the creaminess comes from eggs and starch.", "Work quickly off-heat to avoid scrambled eggs."],
        "description": "A Roman classic of silky egg-and-cheese sauce with crispy pancetta."
    },
    {
        "id": "r002",
        "name": "Chicken Tikka Masala",
        "cuisine": "Indian",
        "diet_tags": ["gluten-free"],
        "allergens": ["milk"],
        "prep_time": "20 min",
        "cook_time": "35 min",
        "servings": 4,
        "difficulty": "Medium",
        "ingredients": ["chicken breast", "yogurt", "tomatoes", "onion", "garlic", "ginger", "garam masala", "cumin", "turmeric", "heavy cream", "butter", "coriander"],
        "instructions": [
            "Marinate chicken in yogurt, garlic, ginger, and spices for at least 1 hour.",
            "Grill or broil chicken until charred. Set aside.",
            "Sauté onions in butter until golden, add garlic and ginger paste.",
            "Add tomatoes and spices; simmer 15 minutes until thick.",
            "Blend sauce until smooth, return to pan.",
            "Add chicken and cream; simmer 10 minutes. Garnish with coriander."
        ],
        "tips": ["Marinate overnight for deeper flavor.", "A pinch of sugar balances the tomato acidity."],
        "description": "Tender grilled chicken in a rich, aromatic tomato-cream sauce."
    },
    {
        "id": "r003",
        "name": "Avocado Toast with Poached Eggs",
        "cuisine": "American",
        "diet_tags": ["vegetarian", "dairy-free"],
        "allergens": ["eggs", "wheat"],
        "prep_time": "5 min",
        "cook_time": "10 min",
        "servings": 2,
        "difficulty": "Easy",
        "ingredients": ["sourdough bread", "avocado", "eggs", "lemon juice", "red pepper flakes", "salt", "black pepper", "olive oil"],
        "instructions": [
            "Toast sourdough slices until golden and crisp.",
            "Mash avocado with lemon juice, salt, and pepper.",
            "Bring water to a gentle simmer; add a splash of vinegar.",
            "Crack each egg into a small cup; slide into simmering water.",
            "Poach 3–4 minutes for a runny yolk.",
            "Spread avocado on toast, top with poached egg, season, and drizzle olive oil."
        ],
        "tips": ["Fresh eggs hold together best when poaching.", "Use a timer — 3 min = runny, 4 min = jammy."],
        "description": "A wholesome, satisfying breakfast classic with creamy avocado and runny eggs."
    },
    {
        "id": "r004",
        "name": "Beef Tacos",
        "cuisine": "Mexican",
        "diet_tags": ["gluten-free-option"],
        "allergens": ["wheat"],
        "prep_time": "15 min",
        "cook_time": "20 min",
        "servings": 4,
        "difficulty": "Easy",
        "ingredients": ["ground beef", "taco shells", "onion", "garlic", "cumin", "chili powder", "paprika", "tomatoes", "lettuce", "cheddar cheese", "sour cream", "lime", "cilantro"],
        "instructions": [
            "Brown ground beef in a skillet over medium-high heat.",
            "Add onion and garlic; cook until softened.",
            "Stir in cumin, chili powder, paprika, salt, and a splash of water.",
            "Simmer 5 minutes until saucy.",
            "Warm taco shells per package directions.",
            "Fill shells with beef, top with lettuce, tomatoes, cheese, sour cream, cilantro, and lime squeeze."
        ],
        "tips": ["Season in layers — season the meat AND the toppings.", "Corn tortillas are naturally gluten-free."],
        "description": "Juicy spiced beef tacos with fresh toppings and a squeeze of lime."
    },
    {
        "id": "r005",
        "name": "Vegetable Stir-Fry",
        "cuisine": "Asian",
        "diet_tags": ["vegan", "gluten-free-option"],
        "allergens": ["soy"],
        "prep_time": "15 min",
        "cook_time": "10 min",
        "servings": 3,
        "difficulty": "Easy",
        "ingredients": ["broccoli", "bell pepper", "carrots", "snap peas", "garlic", "ginger", "soy sauce", "sesame oil", "cornstarch", "vegetable broth", "rice"],
        "instructions": [
            "Cook rice according to package instructions.",
            "Mix soy sauce, vegetable broth, cornstarch, and sesame oil for the sauce.",
            "Heat wok or large skillet on high with oil until smoking.",
            "Add carrots and broccoli; stir-fry 2 minutes.",
            "Add bell pepper, snap peas, garlic, and ginger; stir-fry 2 more minutes.",
            "Pour in sauce; toss until vegetables are coated and sauce thickens. Serve over rice."
        ],
        "tips": ["HIGH heat is the secret to restaurant-quality stir-fry.", "Prep all ingredients before heating the wok — it moves fast!"],
        "description": "Crisp, colorful vegetables in a savory umami sauce, ready in under 25 minutes."
    },
    {
        "id": "r006",
        "name": "Banana Pancakes",
        "cuisine": "American",
        "diet_tags": ["vegetarian", "dairy-free-option"],
        "allergens": ["eggs", "wheat", "milk"],
        "prep_time": "5 min",
        "cook_time": "15 min",
        "servings": 2,
        "difficulty": "Easy",
        "ingredients": ["ripe bananas", "eggs", "flour", "baking powder", "milk", "butter", "vanilla extract", "maple syrup", "salt"],
        "instructions": [
            "Mash bananas in a bowl until smooth.",
            "Whisk in eggs, milk, and vanilla.",
            "Fold in flour, baking powder, and a pinch of salt until just combined.",
            "Heat buttered skillet over medium heat.",
            "Pour 1/4 cup batter per pancake; cook until bubbles form, then flip.",
            "Serve with maple syrup and sliced banana."
        ],
        "tips": ["Overripe bananas are sweeter and easier to mash.", "Don't over-mix — lumps are okay and keep pancakes fluffy."],
        "description": "Fluffy, naturally sweet banana pancakes perfect for a weekend breakfast."
    },
    {
        "id": "r007",
        "name": "Greek Salad",
        "cuisine": "Mediterranean",
        "diet_tags": ["vegetarian", "gluten-free"],
        "allergens": ["milk"],
        "prep_time": "10 min",
        "cook_time": "0 min",
        "servings": 4,
        "difficulty": "Easy",
        "ingredients": ["cucumber", "tomatoes", "red onion", "kalamata olives", "feta cheese", "green bell pepper", "olive oil", "red wine vinegar", "dried oregano", "salt", "black pepper"],
        "instructions": [
            "Chop cucumber, tomatoes, and bell pepper into large chunks.",
            "Thinly slice red onion.",
            "Combine all vegetables and olives in a large bowl.",
            "Whisk together olive oil, red wine vinegar, oregano, salt, and pepper.",
            "Pour dressing over salad and toss gently.",
            "Top with a block or crumbles of feta cheese."
        ],
        "tips": ["Cut vegetables chunky — this is a rustic salad, not a fine dice.", "Add dressing just before serving to keep vegetables crisp."],
        "description": "A fresh, vibrant Mediterranean salad with tangy feta and briny olives."
    },
    {
        "id": "r008",
        "name": "Chocolate Chip Cookies",
        "cuisine": "American",
        "diet_tags": ["vegetarian"],
        "allergens": ["eggs", "wheat", "milk", "soy"],
        "prep_time": "15 min",
        "cook_time": "12 min",
        "servings": 24,
        "difficulty": "Easy",
        "ingredients": ["all-purpose flour", "butter", "brown sugar", "white sugar", "eggs", "vanilla extract", "baking soda", "salt", "chocolate chips"],
        "instructions": [
            "Preheat oven to 375°F (190°C). Line baking sheets with parchment.",
            "Beat softened butter with both sugars until fluffy.",
            "Add eggs and vanilla; mix well.",
            "Whisk flour, baking soda, and salt; gradually fold into butter mixture.",
            "Stir in chocolate chips.",
            "Drop rounded tablespoons onto baking sheets 2 inches apart.",
            "Bake 9–11 minutes until golden on edges. Cool on pan 5 minutes."
        ],
        "tips": ["Brown butter first for a nutty, caramel depth of flavor.", "Chill dough 24 hours for thicker, chewier cookies."],
        "description": "Classic chewy chocolate chip cookies with crisp edges and gooey centers."
    },
    {
        "id": "r009",
        "name": "Lentil Soup",
        "cuisine": "Middle Eastern",
        "diet_tags": ["vegan", "gluten-free"],
        "allergens": [],
        "prep_time": "10 min",
        "cook_time": "35 min",
        "servings": 6,
        "difficulty": "Easy",
        "ingredients": ["red lentils", "onion", "garlic", "carrots", "celery", "tomatoes", "cumin", "turmeric", "paprika", "vegetable broth", "lemon juice", "olive oil", "parsley"],
        "instructions": [
            "Sauté diced onion, carrots, and celery in olive oil until softened.",
            "Add garlic and spices; cook 1 minute until fragrant.",
            "Add rinsed lentils, tomatoes, and vegetable broth.",
            "Bring to a boil, then simmer 25–30 minutes until lentils are tender.",
            "Blend half the soup for a creamy-chunky texture.",
            "Finish with lemon juice, salt, and fresh parsley."
        ],
        "tips": ["Red lentils dissolve — green lentils hold shape if you prefer more texture.", "A drizzle of chili oil on top elevates the presentation."],
        "description": "A hearty, comforting vegan soup packed with protein and warming spices."
    },
    {
        "id": "r010",
        "name": "Garlic Butter Shrimp",
        "cuisine": "American",
        "diet_tags": ["gluten-free", "keto"],
        "allergens": ["shellfish", "milk"],
        "prep_time": "10 min",
        "cook_time": "8 min",
        "servings": 4,
        "difficulty": "Easy",
        "ingredients": ["shrimp", "butter", "garlic", "lemon juice", "parsley", "red pepper flakes", "salt", "black pepper", "olive oil"],
        "instructions": [
            "Pat shrimp dry and season with salt and pepper.",
            "Heat olive oil in a large skillet over high heat.",
            "Cook shrimp in a single layer 1–2 minutes per side until pink. Remove.",
            "Reduce heat to medium; melt butter, add minced garlic and pepper flakes.",
            "Sauté garlic 1 minute until fragrant.",
            "Return shrimp to pan; toss with garlic butter and lemon juice.",
            "Garnish with parsley. Serve immediately."
        ],
        "tips": ["Dry shrimp = better sear. Wet shrimp steam instead of sear.", "Don't crowd the pan — cook in batches if needed."],
        "description": "Succulent shrimp bathed in garlicky, lemony butter — ready in under 20 minutes."
    },
    {
        "id": "r011",
        "name": "Mushroom Risotto",
        "cuisine": "Italian",
        "diet_tags": ["vegetarian", "gluten-free"],
        "allergens": ["milk"],
        "prep_time": "10 min",
        "cook_time": "35 min",
        "servings": 4,
        "difficulty": "Hard",
        "ingredients": ["arborio rice", "mushrooms", "onion", "garlic", "white wine", "vegetable broth", "parmesan cheese", "butter", "olive oil", "thyme", "salt", "black pepper"],
        "instructions": [
            "Warm broth in a separate pot; keep at a gentle simmer.",
            "Sauté mushrooms in olive oil until golden; set aside.",
            "In the same pot, cook diced onion until translucent. Add garlic.",
            "Add arborio rice; stir to coat with oil. Toast 2 minutes.",
            "Pour in wine; stir until absorbed.",
            "Add warm broth one ladle at a time, stirring constantly until absorbed before adding more.",
            "After ~25 minutes, rice should be creamy and al dente.",
            "Stir in mushrooms, butter, and parmesan. Season and serve."
        ],
        "tips": ["Never rush risotto — constant stirring releases starch for creaminess.", "The final 'mantecatura' (cold butter stir-in) is what makes it glossy."],
        "description": "Luxuriously creamy Italian rice with earthy mushrooms and aged parmesan."
    },
    {
        "id": "r012",
        "name": "Mango Smoothie Bowl",
        "cuisine": "American",
        "diet_tags": ["vegan", "gluten-free", "dairy-free"],
        "allergens": [],
        "prep_time": "10 min",
        "cook_time": "0 min",
        "servings": 1,
        "difficulty": "Easy",
        "ingredients": ["frozen mango", "banana", "coconut milk", "granola", "fresh berries", "chia seeds", "honey", "shredded coconut"],
        "instructions": [
            "Blend frozen mango, banana, and coconut milk until thick and smooth.",
            "Pour into a bowl — it should be thicker than a drinkable smoothie.",
            "Arrange granola, fresh berries, chia seeds, and coconut as toppings.",
            "Drizzle with honey. Serve immediately."
        ],
        "tips": ["Use frozen fruit — it keeps the base thick without ice dilution.", "Keep toppings in sections for an Instagram-worthy presentation."],
        "description": "A vibrant, refreshing tropical smoothie bowl packed with nutrients."
    },
]


# ---------------------------------------------------------------------------
# HELPERS — pure-Python text utilities (no external deps)
# ---------------------------------------------------------------------------

# Common English stop words to ignore during tokenisation
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "be", "by", "from", "as", "it",
    "its", "this", "that", "i", "my", "me", "we", "you", "your",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, drop stop-words, return word list."""
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _build_tfidf(documents: list[str]) -> tuple[list[dict], list[int]]:
    """
    Compute TF-IDF vectors for a list of documents.
    Returns (doc_vectors, df_counts) where each doc_vector is a
    dict mapping term -> tfidf weight.
    """
    n = len(documents)
    tokenized = [_tokenize(d) for d in documents]

    # Document frequency: how many docs contain each term
    df: dict[str, int] = {}
    for tokens in tokenized:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1

    doc_vectors: list[dict] = []
    for tokens in tokenized:
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec: dict[str, float] = {}
        for term, count in tf.items():
            tf_val  = count / total
            idf_val = math.log((n + 1) / (df.get(term, 0) + 1)) + 1.0
            vec[term] = tf_val * idf_val
        doc_vectors.append(vec)

    return doc_vectors


def _cosine(vec_a: dict, vec_b: dict) -> float:
    """Cosine similarity between two sparse TF-IDF dicts."""
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0
    dot    = sum(vec_a[t] * vec_b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# RAG RETRIEVAL ENGINE
# ---------------------------------------------------------------------------
class RecipeRAG:
    """
    Pure-Python TF-IDF Retrieval-Augmented Generation engine.
    No numpy or scikit-learn required — works on any Python 3.8+ interpreter.
    """

    def __init__(self, recipes: list = None):
        self.recipes = recipes or RECIPES
        self._doc_vectors: list[dict] = []
        self._build_index()

    def _build_index(self):
        """Build TF-IDF index from recipe documents."""
        documents = []
        for r in self.recipes:
            # Repeat name 3× and ingredients 2× to weight them more heavily
            doc = " ".join([
                (r["name"] + " ") * 3,
                r.get("description", ""),
                (" ".join(r.get("ingredients", [])) + " ") * 2,
                r.get("cuisine", ""),
                " ".join(r.get("diet_tags", [])),
            ])
            documents.append(doc)
        self._doc_vectors = _build_tfidf(documents)

    def retrieve(self, query: str, top_k: int = None, threshold: float = None) -> list:
        """
        Retrieve the top-k most relevant recipes for a query.
        Returns list of (recipe_dict, similarity_score) tuples, sorted desc.
        """
        k      = top_k    or RAG_SETTINGS["top_k"]
        thresh = threshold or RAG_SETTINGS["similarity_threshold"]

        # Build query vector against the same vocabulary
        query_tokens = _tokenize(query)
        query_tf     = Counter(query_tokens)
        total        = len(query_tokens) or 1
        # Reuse IDF from the index: approximate by treating query terms the same
        n = len(self.recipes)
        query_vec: dict[str, float] = {}
        for term, count in query_tf.items():
            tf_val  = count / total
            # How many docs in our index contain this term?
            df_count = sum(1 for dv in self._doc_vectors if term in dv)
            idf_val = math.log((n + 1) / (df_count + 1)) + 1.0
            query_vec[term] = tf_val * idf_val

        # Score every document
        scores: list[float] = [_cosine(query_vec, dv) for dv in self._doc_vectors]

        # Name keyword bonus
        name_weight  = RAG_SETTINGS["name_weight"]
        query_words  = set(_tokenize(query))
        ing_weight   = RAG_SETTINGS["ingredient_weight"]
        for i, recipe in enumerate(self.recipes):
            name_words    = set(_tokenize(recipe["name"]))
            keyword_bonus = len(query_words & name_words) * name_weight * 0.1
            scores[i]     = scores[i] * ing_weight + keyword_bonus

        # Sort descending, apply threshold
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [
            (self.recipes[idx], float(score))
            for idx, score in ranked[:k]
            if score >= thresh
        ]

    def get_recipe_by_id(self, recipe_id: str) -> dict:
        """Retrieve a single recipe by its ID."""
        for r in self.recipes:
            if r["id"] == recipe_id:
                return r
        return None

    def get_all_recipes(self) -> list:
        """Return the full recipe catalog."""
        return self.recipes

    def format_for_context(self, recipes_with_scores: list) -> str:
        """Format retrieved recipes into a string for LLM context injection."""
        if not recipes_with_scores:
            return "No matching recipes found in the curated database."
        context_parts = ["=== RETRIEVED RECIPES FROM KNOWLEDGE BASE ===\n"]
        for i, (recipe, score) in enumerate(
            recipes_with_scores[:RAG_SETTINGS["max_context_recipes"]], 1
        ):
            context_parts.append(
                f"\n--- Recipe {i}: {recipe['name']} (Relevance: {score:.2f}) ---\n"
                f"Cuisine: {recipe['cuisine']} | Difficulty: {recipe['difficulty']}\n"
                f"Prep: {recipe['prep_time']} | Cook: {recipe['cook_time']} | Serves: {recipe['servings']}\n"
                f"Diet Tags: {', '.join(recipe['diet_tags']) or 'None'}\n"
                f"Allergens: {', '.join(recipe['allergens']) or 'None'}\n"
                f"Description: {recipe['description']}\n"
                f"Ingredients: {', '.join(recipe['ingredients'])}\n"
                f"Instructions: {' | '.join(f'{j+1}. {s}' for j, s in enumerate(recipe['instructions']))}\n"
                f"Tips: {' | '.join(recipe['tips'])}\n"
            )
        return "\n".join(context_parts)


# Module-level singleton
rag_engine = RecipeRAG()
