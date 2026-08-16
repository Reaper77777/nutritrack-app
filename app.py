import streamlit as st
import json
import re
import requests
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="NutriTrack AI Universal", page_icon="🥗", layout="centered")

st.title("🥗 NutriTrack AI")
st.write("Universal food search & photo macro tracker powered by Open Food Facts & AI.")

if "logged_foods" not in st.session_state:
    st.session_state.logged_foods = []

if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("Missing Gemini API Key! Please add GEMINI_API_KEY to your Streamlit App Secrets.")
    st.stop()

# LOCKED MODEL VERSION: gemini-3.7-flash
MODEL_NAME = "gemini-3.7-flash"

def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(text)

def search_open_food_facts(query):
    try:
        url = f"https://us.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=1"
        res = requests.get(url, headers={'User-Agent': 'NutriTrackApp/1.0'}).json()
        if res.get('products'):
            prod = res['products'][0]
            nutr = prod.get('nutriments', {})
            return {
                "food_name": prod.get('product_name', query),
                "calories": float(nutr.get('energy-kcal_100g', 0)) * 0.283495,  # Per oz
                "protein_g": float(nutr.get('proteins_100g', 0)) * 0.283495,
                "carbs_g": float(nutr.get('carbohydrates_100g', 0)) * 0.283495,
                "fat_g": float(nutr.get('fat_100g', 0)) * 0.283495,
                "sugar_g": float(nutr.get('sugars_100g', 0)) * 0.283495
            }
    except Exception:
        pass
    return None

tab1, tab2 = st.tabs(["🔍 Universal Search", "📸 Photo Analyzer"])

# --- TAB 1: TEXT SEARCH ---
with tab1:
    st.subheader("Search Any Food On The Web")
    food_query = st.text_input("Enter any food, restaurant meal, or brand")
    portion_oz = st.number_input("Serving Size (ounces)", value=4.0, step=0.5)

    if st.button("Search Macros"):
        if not food_query:
            st.error("Please enter a food item.")
        else:
            data = None
            with st.spinner("Searching global databases..."):
                # Try Open Food Facts database first
                off_data = search_open_food_facts(food_query)
                if off_data and off_data['calories'] > 0:
                    data = {
                        "food_name": off_data['food_name'],
                        "calories": round(off_data['calories'] * portion_oz, 1),
                        "protein_g": round(off_data['protein_g'] * portion_oz, 1),
                        "carbs_g": round(off_data['carbs_g'] * portion_oz, 1),
                        "fat_g": round(off_data['fat_g'] * portion_oz, 1),
                        "sugar_g": round(off_data['sugar_g'] * portion_oz, 1),
                    }
                
                # Fallback to AI if not found in database
                if not data:
                    try:
                        client = genai.Client(api_key=API_KEY)
                        prompt = f"""
                        Nutritional breakdown for: '{food_query}' ({portion_oz} oz).
                        Return ONLY a JSON object:
                        {{"food_name": "string", "calories": float, "protein_g": float, "carbs_g": float, "fat_g": float, "sugar_g": float}}
                        """
                        response = client.models.generate_content(
                            model=MODEL_NAME,
                            contents=prompt,
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        data = extract_json(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")

            if data:
                st.success(f"Found: **{data['food_name']}** ({portion_oz} oz)")
                st.write(f"**Nutrition:** {data['calories']} kcal | {data['protein_g']}g P | {data['carbs_g']}g C | {data['fat_g']}g F | {data['sugar_g']}g S")

                if st.button("Log Searched Item"):
                    st.session_state.logged_foods.append({
                        "name": data['food_name'],
                        "amount": f"{portion_oz} oz",
                        "calories": float(data['calories']),
                        "protein": float(data['protein_g']),
                        "carbs": float(data['carbs_g']),
                        "fat": float(data['fat_g']),
                        "sugar": float(data['sugar_g'])
                    })
                    st.success(f"Added {data['food_name']} to log!")
                    st.rerun()

# --- TAB 2: PHOTO ANALYZER ---
with tab2:
    st.subheader("Snap or Upload Food Photo")
    image_file = st.file_uploader("Upload meal image", type=["jpg", "jpeg", "png"])
    
    if image_file:
        image = Image.open(image_file)
        st.image(image, caption="Uploaded Meal", use_container_width=True)
        
        if st.button("Analyze Photo Macros"):
            try:
                with st.spinner("Identifying food and estimating macros..."):
                    client = genai.Client(api_key=API_KEY)
                    prompt = """
                    Analyze this image. Identify the meal/food item and estimate its portion size in ounces, total calories, protein (g), carbs (g), fat (g), and sugar (g).
                    Return ONLY a JSON object:
                    {"food_name": "string", "portion_oz": float, "calories": float, "protein_g": float, "carbs_g": float, "fat_g": float, "sugar_g": float}
                    """
                    
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[image, prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    data = extract_json(response.text)
                    
                    st.success(f"Identified: **{data['food_name']}** (~{data['portion_oz']} oz)")
                    st.write(f"**Nutrition:** {data['calories']} kcal | {data['protein_g']}g P | {data['carbs_g']}g C | {data['fat_g']}g F | {data['sugar_g']}g S")
                    
                    if st.button("Log Photo Meal"):
                        st.session_state.logged_foods.append({
                            "name": data['food_name'],
                            "amount": f"~{data['portion_oz']} oz (Photo)",
                            "calories": float(data['calories']),
                            "protein": float(data['protein_g']),
                            "carbs": float(data['carbs_g']),
                            "fat": float(data['fat_g']),
                            "sugar": float(data['sugar_g'])
                        })
                        st.success("Added photo entry to log!")
                        st.rerun()
            except Exception as e:
                st.error(f"Error analyzing image: {e}")

# --- DAILY TOTALS LOG ---
st.markdown("---")
st.subheader("📋 Today's Total Consumed")

if st.session_state.logged_foods:
    total_cal = sum(item["calories"] for item in st.session_state.logged_foods)
    total_prot = sum(item["protein"] for item in st.session_state.logged_foods)
    total_carb = sum(item["carbs"] for item in st.session_state.logged_foods)
    total_fat = sum(item["fat"] for item in st.session_state.logged_foods)
    total_sug = sum(item["sugar"] for item in st.session_state.logged_foods)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Calories", f"{round(total_cal, 1)}")
    col2.metric("Protein", f"{round(total_prot, 1)}g")
    col3.metric("Carbs", f"{round(total_carb, 1)}g")
    col4.metric("Fat", f"{round(total_fat, 1)}g")
    col5.metric("Sugar", f"{round(total_sug, 1)}g")

    st.write("**Logged Items:**")
    for item in st.session_state.logged_foods:
        st.write(f"• **{item['name']}** ({item['amount']}) — {item['calories']} kcal | {item['protein']}g P | {item['carbs']}g C | {item['fat']}g F | {item['sugar']}g S")
    
    if st.button("Clear Today's Log"):
        st.session_state.logged_foods = []
        st.rerun()
else:
    st.info("No food logged yet today.")
