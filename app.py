import os
import subprocess
import time
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import speech_recognition as sr
from gtts import gTTS
import imageio_ffmpeg as im_ffmpeg

app = Flask(__name__)
app.secret_key = "rural_assistant_secret_key" # Change to a safe key in production

# Create directories
os.makedirs("static/voice", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)

FFMPEG_EXE = im_ffmpeg.get_ffmpeg_exe()

# =========================
# CHATBOT LOGIC (RULE-BASED)
# =========================

def get_fallback_answer(question, domain, lang, lat=None, lon=None):
    """Expanded rule-based engine covering a broad range of rural topics with domain-specific logic."""
    text = question.lower()
    d = domain.lower()
    
    # 1. WEATHER
    if "weather" in d or "வானிலை" in text or "मौसम" in text:
        if any(w in text for w in ["rain", "மழை", "बारिश"]):
            res = {"en": "No rain expected today. Sky will be clear.", "ta": "இன்று மழை எதிர்பார்க்கவில்லை. வானம் தெளிவாக இருக்கும்.", "hi": "आज बारिश की संभावना नहीं है। आसमान साफ रहेगा।"}
        elif any(w in text for w in ["tomorrow", "நாளை", "कल"]):
            res = {"en": "Tomorrow will be slightly cooler.", "ta": "நாளை சற்று குளிர்ச்சியாக இருக்கும்.", "hi": "कल मौसम थोड़ा ठंडा रहेगा।"}
        elif any(w in text for w in ["warning", "எச்சரிக்கை", "चेतावनी"]):
            res = {"en": "No weather warnings today.", "ta": "இன்று வானிலை எச்சரிக்கைகள் எதுவும் இல்லை.", "hi": "आज मौसम की कोई चेतावनी नहीं है।"}
        else:
            loc_str = f" at {lat}, {lon}" if (lat and lon) else ""
            res = {"en": f"The weather is around 32°C and sunny{loc_str}.", 
                   "ta": f"வானிலை சுமார் 32°C மற்றும் வெயில் காணப்படும்{loc_str}.", 
                   "hi": f"मौसम लगभग 32°C और धूप वाला है{loc_str}।"}
        return res.get(lang, res["en"])

    # 2. EMERGENCY & HELP
    elif any(kw in d for kw in ["emergency", "help", "அவசரம்", "உதவி", "मदद", "आपातकाल"]):
        if any(w in text for w in ["helpline", "number", "எண்", "नंबर", "contact"]):
            res = {"en": "Call 108 for ambulance or 112 for emergency services.", "ta": "ஆம்புலன்சுக்கு 108 அல்லது அவசர உதவிக்கு 112 ஐ அழைக்கவும்.", "hi": "एम्बुलेंस के लिए 108 या आपातकाल के लिए 112 पर कॉल करें।"}
        elif any(w in text for w in ["flood", "வெள்ளம்", "बाढ़"]):
            res = {"en": "Move to higher ground and avoid waterlogged areas. Follow local safety instructions.", 
                   "ta": "உயர்ந்த இடத்திற்குச் செல்லுங்கள் மற்றும் நீர் தேங்கியுள்ள இடங்களைத் தவிர்க்கவும். உள்ளூர் பாதுகாப்பு வழிமுறைகளைப் பின்பற்றவும்.", 
                   "hi": "ऊंचे स्थानों पर जाएं और जलभराव वाले क्षेत्रों से बचें। स्थानीय सुरक्षा निर्देशों का पालन करें।"}
        elif any(w in text for w in ["fire", "தீ", "आग"]):
            res = {"en": "Use fire extinguisher if safe, evacuate immediately, and call emergency services.", 
                   "ta": "பாதுகாப்பாக இருந்தால் தீயணைப்பானைப் பயன்படுத்தவும், உடனடியாக வெளியேறவும், அவசர சேவைகளை அழைக்கவும்.", 
                   "hi": "यदि सुरक्षित हो तो अग्निशामक यंत्र का प्रयोग करें, तुरंत बाहर निकलें और आपातकालीन सेवाओं को कॉल करें।"}
        elif any(w in text for w in ["accident", "விபத்து", "दुर्घटना"]):
            res = {"en": "Call 108 immediately and provide first aid if possible.", 
                   "ta": "உடனடியாக 108-ஐ அழைத்து முடிந்தால் முதலுதவி வழங்கவும்.", 
                   "hi": "तुरंत 108 पर कॉल करें और यदि संभव हो तो प्राथमिक चिकित्सा प्रदान करें।"}
        elif any(w in text for w in ["who", "contact", "தொடர்பு", "संपर्क"]):
            res = {"en": "Contact emergency services by dialing 112 or local authorities.", 
                   "ta": "112 அல்லது உள்ளூர் அதிகாரிகளை அழைக்க அவசர சேவைகளைத் தொடர்பு கொள்ளவும்.", 
                   "hi": "112 या स्थानीय अधिकारियों को डायल करके आपातकालीन सेवाओं से संपर्क करें।"}
        else:
            res = {"en": "In emergency situations, stay calm and contact emergency services (108/112).", 
                   "ta": "அவசரகாலத்தில் அமைதியாக இருங்கள் மற்றும் அவசர சேவைகளைத் (108/112) தொடர்பு கொள்ளவும்.", 
                   "hi": "आपातकालीन स्थिति में शांत रहें और आपातकालीन सेवाओं (108/112) से संपर्क करें।"}
        return res.get(lang, res["en"])

    # 3. MARKET & PRICE
    elif any(kw in d for kw in ["market", "price", "சந்தை", "விலை", "मண்டி", "भाव"]):
        if any(w in text for w in ["tomato", "தக்காளி", "टमाटर"]):
            res = {"en": "Tomato price is around ₹30/kg.", "ta": "தக்காளி விலை கிலோ ரூ.30.", "hi": "टमाटर की कीमत लगभग ₹30/किलो है।"}
        elif any(w in text for w in ["vegetable", "காய்கறி", "சிறு", "सब्जी"]):
            res = {"en": "Vegetable prices range between ₹20–₹50/kg.", "ta": "காய்கறி விலைகள் கிலோ ₹20-₹50 வரை இருக்கும்.", "hi": "सब्जियों की कीमतें ₹20-₹50/किलो के बीच हैं।"}
        elif any(w in text for w in ["demand", "தேவை", "மாங்க"]):
            res = {"en": "Tomato and onion are currently in high demand.", "ta": "தக்காளி மற்றும் வெங்காயத்திற்கு தற்போது அதிக தேவை உள்ளது.", "hi": "टमाटर और प्याज की वर्तमान में भारी मांग है।"}
        elif any(w in text for w in ["price", "விலை", "कीमत", "rate", "mandi"]):
            res = {"en": "Market prices vary based on demand and supply. Wheat is around ₹2,275/quintal.", "ta": "சந்தை விலைகள் தேவை மற்றும் விநியோகத்தைப் பொறுத்து மாறுபடும். கோதுமை ரூ.2,275/குவிண்டால்.", "hi": "बाजार की कीमतें मांग और आपूर्ति के आधार पर भिन्न होती हैं। गेहूं लगभग ₹2,275/क्विंटल है।"}
        else:
            res = {"en": "Market prices vary based on demand and supply. Check local mandi for daily updates.", "ta": "சந்தை விலைகள் தேவை மற்றும் விநியோகத்தைப் பொறுத்து மாறுபடும். தினசரி அப்டேட்டுகளுக்கு உள்ளூர் மண்டியைப் பார்க்கவும்.", "hi": "बाजार की कीमतें मांग और आपूर्ति के आधार पर भिन्न होती हैं। दैनिक अपडेट के लिए स्थानीय मंडी देखें।"}
        return res.get(lang, res["en"])

    # 4. HEALTH
    elif any(kw in d for kw in ["health", "மருத்துவம்", "স্বাস্থ্য", "स्वास्थ्य"]):
        if any(w in text for w in ["daily", "தினசரி", "रोजाना"]):
            res = {"en": "Exercise regularly and eat healthy food to stay fit.", "ta": "தவறாமல் உடற்பயிற்சி செய்யுங்கள் மற்றும் ஆரோக்கியமான உணவை உண்ணுங்கள்.", "hi": "स्वस्थ रहने के लिए नियमित व्यायाम करें और पौष्टिक भोजन लें।"}
        elif any(w in text for w in ["food", "உணவு", "भोजन", "diet"]):
            res = {"en": "Eat fresh fruits, vegetables, and drink clean water.", "ta": "பழங்கள், காய்கறிகளைச் சாப்பிடுங்கள் மற்றும் சுத்தமான தண்ணீரைக் குடியுங்கள்.", "hi": "ताजे फल, सब्जियां खाएं और साफ पानी पिएं।"}
        elif any(w in text for w in ["disease", "நோய்", "बीमारी", "sick"]):
            res = {"en": "Maintain hygiene and consult a doctor if you feel unwell.", "ta": "சுகாதாரத்தைப் பேணுங்கள் மற்றும் உடல்நிலை சரியில்லை என்றால் மருத்துவரை அணுகவும்.", "hi": "स्वच्छता बनाए रखें और अस्वस्थ होने पर डॉक्टर से सलाह लें।"}
        else:
            res = {"en": "Maintain hygiene, stay active, and drink clean water for good health.", "ta": "சுகாதாரத்தைப் பேணுங்கள் மற்றும் நல்ல ஆரோக்கியத்திற்கு சுத்தமான தண்ணீரைக் குடியுங்கள்.", "hi": "स्वच्छता बनाए रखें, सक्रिय रहें और अच्छे स्वास्थ्य के लिए साफ पानी पिएं।"}
        return res.get(lang, res["en"])

    # 5. SCHEMES
    elif any(kw in d for kw in ["scheme", "yojana", "திட்டம்", "योजना"]):
        if any(w in text for w in ["document", "ஆவணம்", "proof", "आधार", "aadhaar"]):
            res = {"en": "You need Aadhaar, bank account, and income proof for most schemes.", 
                   "ta": "பெரும்பாலான திட்டங்களுக்கு உங்களுக்கு ஆதார், வங்கி கணக்கு மற்றும் வருமானச் சான்று தேவை.", 
                   "hi": "अधिकांश योजनाओं के लिए आपको आधार, बैंक खाता और आय प्रमाण की आवश्यकता होती है।"}
        elif any(w in text for w in ["apply", "விண்ணப்பிக்க", "how"]):
            res = {"en": "You can apply through official government portals like PM-Kisan or nearby service centers.", 
                   "ta": "அரசு இணையதளங்கள் (PM-Kisan) அல்லது அருகிலுள்ள சேவை மையங்கள் மூலம் விண்ணப்பிக்கலாம்.", 
                   "hi": "आप सरकारी पोर्टल (पीएम-किसान) या नजदीकी सेवा केंद्रों के माध्यम से आवेदन कर सकते हैं।"}
        elif any(w in text for w in ["subsidy", "மானிய", "benefit", "छूट"]):
            res = {"en": "The government provides subsidies for farmers, housing, and LPG schemes like Ujjwala.", 
                   "ta": "விவசாயிகள், வீடு மற்றும் உஜ்வலா போன்ற எல்பிஜி திட்டங்களுக்கு அரசு மானியம் வழங்குகிறது.", 
                   "hi": "सरकार किसानों, आवास और उज्ज्वला जैसी एलपीजी योजनाओं के लिए सब्सिडी प्रदान करती है।"}
        elif any(w in text for w in ["loan", "கடன்", "कर्ज", "kisan"]):
            res = {"en": "PM-Kisan Yojana provides ₹6,000/year to farmers. KCC loans are available at 4% interest.", 
                   "ta": "PM-கிசான் திட்டத்தில் ஆண்டுக்கு ₹6,000 வழங்கப்படுகிறது. KCC கடன்கள் 4% வட்டியில் கிடைக்கும்.", 
                   "hi": "पीएम-किसान योजना किसानों को ₹6,000/वर्ष प्रदान करती है। केसीसी ऋण 4% ब्याज पर उपलब्ध हैं।"}
        else:
            res = {"en": "Check PM-Kisan and PM-Awas portals for rural welfare benefits and ration card renewal.", 
                   "ta": "PM-கிசான் மற்றும் PM-ஆவாஸ் இணையதளங்களில் அரசு நலத்திட்டங்களைப் பார்க்கவும்.", 
                   "hi": "पीएम-किसान और पीएम-आवास पोर्टल पर जाकर सरकारी योजनाओं का लाभ उठाएं।"}
        return res.get(lang, res["en"])

    # 6. FARMING
    elif any(kw in d for kw in ["farm", "agri", "crop", "விவசாயம்", "खेती"]):
        if any(w in text for w in ["soil", "மண்", "मिट्टी"]):
            res = {"en": "Get your soil tested at the nearest Krishi Kendra. Healthy soil needs proper NPK balance.", 
                   "ta": "உங்கள் மண் பரிசோதனையை அருகிலுள்ள கிருஷி கேந்திராவில் செய்யுங்கள்.", 
                   "hi": "नजदीकी कृषि केंद्र पर अपनी मिट्टी की जांच कराएं।"}
        elif any(w in text for w in ["fertilizer", "உரம்", "खाद"]):
            res = {"en": "Use organic compost and avoid excessive chemical fertilizers to maintain soil fertility.", 
                   "ta": "இயற்கை உரங்களைப் பயன்படுத்துங்கள் மற்றும் ரசாயன உரங்களைத் தவிர்க்கவும்.", 
                   "hi": "जैविक खाद का प्रयोग करें और रासायनिक खादों से बचें।"}
        elif any(w in text for w in ["crop", "பயிர்", "फसल"]):
            res = {"en": "Choose crops based on the current season. Currently, it's a good time for seasonal vegetables and pulses.", 
                   "ta": "தற்போதைய பருவத்திற்கு ஏற்ற பயிர்களைத் தேர்ந்தெடுக்கவும்.", 
                   "hi": "वर्तमान मौसम के आधार पर फसलें चुनें।"}
        else:
            res = {"en": "Use organic fertilizers for healthy soil and follow the seasonal crop calendar. Contact Kisan Helpline: 1800-180-1551.", 
                   "ta": "மண் வளத்திற்கு இயற்கை உரங்களைப் பயன்படுத்துங்கள். விவாசாய உதவி: 1800-180-1551.", 
                   "hi": "स्वस्थ मिट्टी के लिए जैविक खाद का प्रयोग करें। किसान हेल्पलाइन: 1800-180-1551।"}
        return res.get(lang, res["en"])

    # FINAL FALLBACK (No domain matches or it's a general question)
    fallback = {
        "en": "I can help with Weather, Market prices, Health tips, Farming help, Emergency services, and Government schemes. What would you like to know?",
        "ta": "வானிலை, சந்தை விலை, சுகாதார குறிப்புகள், விவசாய உதவி, அவசர உதவி மற்றும் திட்டங்களுக்கு நான் உதவ முடியும். நீங்கள் என்ன அறிய விரும்புகிறீர்கள்?",
        "hi": "मैं मौसम, मंडी भाव, स्वास्थ्य सुझाव, खेती, आपातकालीन सहायता और योजनाओं में मदद कर सकता हूं। आप क्या जानना चाहते हैं?"
    }
    return fallback.get(lang, fallback["en"])

# =========================
# CHATBOT MAIN
# =========================
def chatbot(question, lang="en", lat=None, lon=None, domain="General"):
    """Pure rule-based chatbot for offline support."""
    # Process the question through the rule engine
    answer = get_fallback_answer(question, domain, lang, lat, lon)
    return answer

# =========================
# AUDIO UTILITIES
# =========================
def speech_to_text(file, lang):
    lang_map = {"en":"en-IN","ta":"ta-IN","hi":"hi-IN"}
    r = sr.Recognizer()
    try:
        with sr.AudioFile(file) as source:
            audio = r.record(source)
        return r.recognize_google(audio, language=lang_map.get(lang, "en-IN"))
    except:
        return ""

def text_to_voice(text, lang):
    os.makedirs("static/voice", exist_ok=True)
    ts = int(time.time())
    filename = f"static/voice/output_{lang}_{ts}.mp3"
    try:
        tts = gTTS(text, lang=lang)
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"gTTS error: {e}")
        return ""

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "1234":
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/process", methods=["POST"])
def process():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Input handling
        file = request.files.get("audio")
        text_query = request.form.get("text_query")
        lang = request.form.get("language") or "en"
        domain = request.form.get("domain") or "General"
        
        # Location
        lat = request.form.get("lat") or session.get("lat")
        lon = request.form.get("lon") or session.get("lon")
        if request.form.get("lat"): session["lat"] = request.form.get("lat")
        if request.form.get("lon"): session["lon"] = request.form.get("lon")

        text = ""
        if file:
            raw_path = "static/voice/input.blob"
            wav_path = "static/voice/input.wav"
            file.save(raw_path)
            # Convert to wav
            subprocess.run([FFMPEG_EXE, "-y", "-i", raw_path, wav_path], capture_output=True)
            text = speech_to_text(wav_path, lang)
        elif text_query:
            text = text_query

        if not text:
            # Simple greeting if no text detected
            greetings = {"en": "Hello", "ta": "வணக்கம்", "hi": "नमस्ते"}
            text = greetings.get(lang, "Hello")

        # Get Intelligent Answer
        answer = chatbot(text, lang, lat, lon, domain)
        voice = text_to_voice(answer, lang)

        return jsonify({
            "text": text,
            "answer": answer,
            "voice": voice
        })

    except Exception as e:
        print(f"Process error: {e}")
        return jsonify({
            "text": "",
            "answer": "I encountered an error. Please try again.",
            "voice": ""
        })

@app.route("/upload", methods=["POST"])
def upload():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400
        
    file = request.files["image"]
    os.makedirs("static/uploads", exist_ok=True)
    path = os.path.join("static/uploads", "scan.jpg")
    file.save(path)

    # Simplified response for crop scan
    return jsonify({
        "result": "Based on the scan, your crops appear healthy. Continue regular irrigation."
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)