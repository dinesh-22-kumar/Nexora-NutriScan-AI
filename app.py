import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Nexora NutriScan AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# விரிவான உணவு சேர்க்கைகள் & மூலப்பொருள் அறிவுத்தளம்
INGREDIENT_DATABASE = {
    # மறைமுக சர்க்கரைகள் (Hidden Sugars)
    "maltodextrin": {"risk": "High", "category": "Hidden Sugar", "desc": "இரத்தத்தில் சர்க்கரை அளவை மிக வேகமாக உயர்த்தும் (Very High Glycemic Index)."},
    "high fructose corn syrup": {"risk": "High", "category": "Hidden Sugar", "desc": "கல்லீரல் கொழுப்பு மற்றும் உடல் பருமனை அதிகரிக்கும்."},
    "invert sugar": {"risk": "Medium", "category": "Hidden Sugar", "desc": "செயற்கை முறையில் பிரிக்கப்பட்ட குளுக்கோஸ் & பிரக்டோஸ்."},
    "dextrose": {"risk": "Medium", "category": "Hidden Sugar", "desc": "சுத்திகரிக்கப்பட்ட எளிய சர்க்கரை வகை."},
    "sucrose": {"risk": "Medium", "category": "Sugar", "desc": "சாதாரண சர்க்கரை அளவு அதிகம்."},
    "glucose syrup": {"risk": "High", "category": "Hidden Sugar", "desc": "சுத்திகரிக்கப்பட்ட அடர்ந்த இனிப்பூட்டி."},
    "liquid glucose": {"risk": "High", "category": "Hidden Sugar", "desc": "அதிக இனிப்புச் செறிவு கொண்ட சுத்திகரிக்கப்பட்ட திரவ சர்க்கரை."},
    "malt extract": {"risk": "Low", "category": "Sweetener", "desc": "தானியத்திலிருந்து எடுக்கப்படும் சர்க்கரை."},

    # ஆரோக்கியமற்ற கொழுப்புகள் (Unhealthy Fats)
    "palm oil": {"risk": "High", "category": "Unhealthy Fat", "desc": "அதிகப்படியான Saturated Fat; இதய ஆரோக்கியத்திற்கு உகந்தது அல்ல."},
    "palmolein": {"risk": "High", "category": "Unhealthy Fat", "desc": "சுத்திகரிக்கப்பட்ட பாமாயில் திரவம்."},
    "hydrogenated vegetable oil": {"risk": "Severe", "category": "Trans Fat", "desc": "ஆபத்தான டிரான்ஸ்-ஃபேட் (Trans Fat); கெட்ட கொலஸ்ட்ராலை அதிகரிக்கும்."},
    "interesterified fat": {"risk": "High", "category": "Industrial Fat", "desc": "தொழிற்சாலை முறையில் மாற்றியமைக்கப்பட்ட கொழுப்பு."},
    "margarine": {"risk": "High", "category": "Trans/Saturated Fat", "desc": "செயற்கை வெண்ணெய்; டிரான்ஸ் ஃபேட் அபாயம் அதிகம்."},

    # ஆபத்தான INS / E குறியீடுகள் (Chemical Additives)
    "ins 621": {"risk": "High", "category": "Flavor Enhancer (MSG)", "desc": "அஜினோமோட்டோ (Monosodium Glutamate); சிலருக்கு தலைவலி/ஒவ்வாமை வரலாம்."},
    "e621": {"risk": "High", "category": "Flavor Enhancer (MSG)", "desc": "MSG குறியீடு (Monosodium Glutamate)."},
    "ins 627": {"risk": "Medium", "category": "Flavor Enhancer", "desc": "Disodium guanylate; சுவையூட்டும் ரசாயன சேர்க்கை."},
    "ins 631": {"risk": "Medium", "category": "Flavor Enhancer", "desc": "Disodium inosinate; செயற்கை சுவையூட்டி."},
    "ins 150d": {"risk": "High", "category": "Caramel Color", "desc": "அம்மோனியா சேர்க்கப்பட்ட செயற்கை நிறமூட்டி (Soft drinks & sauces)."},
    "e150d": {"risk": "High", "category": "Caramel Color", "desc": "Sulfite ammonia caramel."},
    "ins 102": {"risk": "High", "category": "Synthetic Color (Tartrazine)", "desc": "செயற்கை மஞ்சள் நிறம்; குழந்தைகளுக்கு அதீத சுறுசுறுப்பு (Hyperactivity) வரலாம்."},
    "ins 110": {"risk": "High", "category": "Synthetic Color (Sunset Yellow)", "desc": "செயற்கை ஆரஞ்சு நிறமூட்டி."},
    "ins 122": {"risk": "High", "category": "Synthetic Color (Azorubine)", "desc": "செயற்கை சிவப்பு நிறமூட்டி; அலர்ஜி உண்டாக்கலாம்."},
    "ins 211": {"risk": "Medium", "category": "Preservative (Sodium Benzoate)", "desc": "செயற்கை பதனப்பொருள் (Chemical preservative)."},
    "ins 223": {"risk": "Medium", "category": "Preservative (Sodium Metabisulphite)", "desc": "ஆஸ்துமா உள்ளவர்களுக்கு மூச்சுத்திணறல் ஏற்படுத்தலாம்."},
    "ins 320": {"risk": "High", "category": "Antioxidant (BHA)", "desc": "செயற்கை ஆண்டி-ஆக்சிடன்ட்."},
    "ins 951": {"risk": "High", "category": "Artificial Sweetener (Aspartame)", "desc": "ஜீரோ-சுகர் செயற்கை இனிப்பு; அதிகம் உட்கொள்வது நல்லதல்ல."},
    "ins 950": {"risk": "Medium", "category": "Artificial Sweetener (Acesulfame K)", "desc": "செயற்கை இனிப்பூட்டி."},
    "ins 955": {"risk": "Medium", "category": "Artificial Sweetener (Sucralose)", "desc": "குடல் நுண்ணுயிரிகளைப் பாதிக்க வாய்ப்புள்ளது."},
    
    # பொதுவான அலர்ஜி காரணிகள் (Allergens)
    "gluten": {"risk": "Allergen", "category": "Allergen", "desc": "கோதுமை அலர்ஜி உள்ளவர்கள் தவிர்க்கவும்."},
    "soy lecithin": {"risk": "Allergen", "category": "Emulsifier / Allergen", "desc": "சோயா ஒவ்வாமை உள்ளவர்களுக்கு சிக்கல் வரலாம்."},
    "ins 322": {"risk": "Allergen", "category": "Emulsifier (Lecithin)", "desc": "பொதுவாக சோயாவிலிருந்து பெறப்படும் லெசித்தின்."},
    "peanut": {"risk": "Allergen", "category": "Allergen", "desc": "கடலை ஒவ்வாமை உள்ளவர்கள் கண்டிப்பாக தவிர்க்கவும்."},
    "milk solids": {"risk": "Allergen", "category": "Dairy Allergen", "desc": "Lactose Intolerance உள்ளவர்கள் கவனமாக இருக்கவும்."}
}

FOOD_KEYWORDS = [
    "flour", "oil", "sugar", "salt", "water", "milk", "flavor", "flavour", 
    "acid", "extract", "powder", "syrup", "fat", "ins", "e-", "gluten", 
    "cocoa", "butter", "starch", "wheat", "protein", "preservative", 
    "color", "colour", "emulsifier", "acidity", "cream", "masala", "spices"
]

class IngredientRequest(BaseModel):
    ingredients_text: str

@app.post("/analyze-food")
def analyze_food(req: IngredientRequest):
    raw_text = req.ingredients_text.lower().strip()
    
    if len(raw_text) < 4:
        raise HTTPException(
            status_code=400, 
            detail="டெக்ஸ்ட் எதுவும் கண்டறியப்படவில்லை. பாக்கெட் உணவின் Ingredients பகுதியைத் தெளிவாகப் படம் பிடிக்கவும்."
        )

    found_flags = []
    penalty_points = 0
    allergens = []

    for item, info in INGREDIENT_DATABASE.items():
        pattern = r'\b' + re.escape(item) + r'\b'
        if re.search(pattern, raw_text):
            risk_level = info["risk"]
            category = info["category"]
            
            if risk_level == "Severe":
                penalty_points += 40
            elif risk_level == "High":
                penalty_points += 25
            elif risk_level == "Medium":
                penalty_points += 15
            elif risk_level == "Low":
                penalty_points += 5
            elif risk_level == "Allergen":
                allergens.append(item.title())

            found_flags.append({
                "name": item.upper() if "ins" in item or "e" in item else item.title(),
                "category": category,
                "risk": risk_level,
                "tamil_explanation": info["desc"]
            })

    has_food_words = any(re.search(r'\b' + re.escape(kw) + r'\b', raw_text) for kw in FOOD_KEYWORDS)

    if not found_flags and not has_food_words:
        return {
            "health_score": 0,
            "grade": "N/A",
            "badge": "🔍 No Food Ingredients Recognized",
            "verdict": "படத்தில் உணவு மூலப்பொருள் விவரங்கள் எதுவும் தெளிவாக இல்லை. பாக்கெட் உணவின் பின்புறக் குறிப்புகளை வெளிச்சத்தில் வைத்து ஸ்கேன் செய்யவும்.",
            "flags_count": 0,
            "detected_items": [],
            "allergens": []
        }

    health_score = max(10, 100 - penalty_points)
    
    if health_score >= 85:
        grade = "A"
        badge = "🌿 Very Safe / Clean"
        verdict = "இந்த உணவு பெருமளவில் இயற்கையானது மற்றும் குறைவான சேர்க்கைகளுடன் பாதுகாப்பானது."
    elif health_score >= 65:
        grade = "B"
        badge = "⚖️ Moderate / Consume Occasionally"
        verdict = "மிதமான பதனப்பொருட்கள் உள்ளன; எப்போதாவது உட்கொள்ளலாம்."
    elif health_score >= 40:
        grade = "C"
        badge = "⚠️ High Processed / Caution"
        verdict = "அதிகப்படியான சுத்திகரிக்கப்பட்ட சர்க்கரை/பாமாயில் அல்லது நிறமூட்டிகள் உள்ளன; அடிக்கடி உண்பதைத் தவிர்க்கவும்."
    else:
        grade = "D"
        badge = "🚫 Ultra Processed / Avoid"
        verdict = "ஆபத்தான டிரான்ஸ்-ஃபேட் அல்லது அதிக ரசாயன சேர்க்கைகள் உள்ளன; உடலுக்கு உகந்தது அல்ல."

    return {
        "health_score": health_score,
        "grade": grade,
        "badge": badge,
        "verdict": verdict,
        "flags_count": len(found_flags),
        "detected_items": found_flags,
        "allergens": list(set(allergens))
    }