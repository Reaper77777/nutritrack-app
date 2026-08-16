%%writefile app.py
import streamlit as st
import json
import re
import io
import base64
from PIL import Image
from google import genai

st.set_page_config(page_title="NutriTrack AI Universal", page_icon="🥗", layout="centered")

st.title("🥗 NutriTrack AI")
st.write("Universal food search & photo macro tracker powered by live web data.")

if "logged_foods" not in st.session_state:
    st.session_state.logged_foods = []

# API Key
API_KEY = "AQ.Ab8RN6Kd-R0YXF4G5_CeeFY4bwHxPPlElDFswBX-Okgoe6-8_A"

# Updated to current active model string
MODEL_NAME = "gemini-3.6-flash"

def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(text)

tab1, tab2 = st.tabs(["🔍 Universal Search", "📸 Photo Analyzer"])

# --- TAB 1: TEXT SEARCH ---
with tab1:
    st.subheader("Search Any Food On The Web")
    food_query = st.text_input("Enter any food, restaurant meal, or brand (e.g., Chipotle Chicken Bowl, In-N-Out Double Double, Honeycrisp Apple)")
    portion_oz = st.number_input("Serving Size (ounces)", value=4.0, step=0.5)

    if st.button("Search Macros"):
        if not food_query:
            st.error("Please enter a food item.")
        else:
            try:
                with st.spinner("Searching global nutrition databases..."):
                    client = genai.Client(api_key=API_KEY)
                    prompt = f"""
                    Search for accurate nutritional information for: '{food_query}'.
                    Calculate the nutritional breakdown for a serving size of exactly {portion_oz} ounces.
                    Return ONLY a JSON object with these keys:
                    {{"food_name": "string", "calories": float, "protein_g": float, "carbs_g": float, "fat_g": float, "sugar_g": float}}
                    """
                    
                    interaction = client.interactions.create(
                        model=MODEL_NAME,
                        input=prompt
                    )
                    
                    data = extract_json(interaction.output_text)

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
            except Exception as e:
                st.error(f"Error fetching macros: {e}")

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
                    
                    buffered = io.BytesIO()
                    image.convert("RGB").save(buffered, format="JPEG")
                    image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    
                    prompt = """
                    Analyze this image. Identify the meal/food item and estimate its portion size in ounces, total calories, protein (g), carbs (g), fat (g), and sugar (g).
                    Return ONLY a JSON object with these keys:
                    {"food_name": "string", "portion_oz": float, "calories": float, "protein_g": float, "carbs_g": float, "fat_g": float, "sugar_g": float}
                    """
                    
                    interaction = client.interactions.create(
                        model=MODEL_NAME,
                        input=[
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "mime_type": "image/jpeg",
                                "data": image_b64
                            }
                        ]
                    )
                    
                    data = extract_json(interaction.output_text)
                    
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
