/** 
 * static/script.js 
 * Smart Rural Digital Assistant - Premium Interaction Engine
 */

// Global State
let userLat = null;
let userLon = null;
let currentLang = 'en'; 
let voiceActive = false;
let mediaRecorder = null;
let audioChunks = [];
let autoStopTimer = null;
let selectedDomain = "";

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    addChatBubble("assistant", "I am successfully logged in and ready. Tap a topic or click the mic to speak.");
    
    // Proactive location request on start
    setTimeout(getLocation, 1500); 
});

// Language Data Structure
const translations = {
  en: ["Weather", "Market", "Health", "Farming", "Schemes", "Emergency"],
  ta: ["வானிலை", "சந்தை", "சுகாதாரம்", "விவசாயம்", "அரசு திட்டங்கள்", "அவசரம்"],
  hi: ["मौसम", "बाजार", "स्वास्थ्य", "खेती", "सरकारी योजनाएं", "आपातकाल"]
};

// UI Helper: Language Switcher
function changeLanguage(lang) {
    currentLang = lang;
    
    // Update domain cards text instantly
    document.getElementById("card1").innerText = translations[lang][0];
    document.getElementById("card2").innerText = translations[lang][1];
    document.getElementById("card3").innerText = translations[lang][2];
    document.getElementById("card4").innerText = translations[lang][3];
    document.getElementById("card5").innerText = translations[lang][4];
    document.getElementById("card6").innerText = translations[lang][5];

    // Update Welcome Text
    const welcomeTitle = { 'en': 'Namaste! 🙏', 'ta': 'வணக்கம்! 🙏', 'hi': 'नमस्ते! 🙏' };
    const welcomeBody = { 
        'en': 'Welcome to your rural assistant. How can I help you?',
        'ta': 'உங்கள் கிராமப்புற உதவியாளருக்கு வரவேற்கிறோம். நான் உங்களுக்கு எப்படி உதவ முடியும்?',
        'hi': 'आपके ग्रामीण सहायक में आपका स्वागत है। मैं आपकी कैसे मदद कर सकता हूँ?'
    };
    document.getElementById("welcome-text").innerText = welcomeTitle[lang];
    document.getElementById("welcome-sub").innerText = welcomeBody[lang];

    // Update pill highlights
    document.querySelectorAll('.lang-pill').forEach(pill => {
        if (pill.dataset.lang === lang) {
            pill.classList.add('active');
        } else {
            pill.classList.remove('active');
        }
    });

    console.log(`Language changed to: ${lang}`);
}

// UI Helper: Feature Cards Quick Ask
function askQuick(topic) {
    selectedDomain = topic;
    
    const domainPrompts = {
        'weather': { 'en': 'Please ask your question about Weather', 'ta': 'வானிலை பற்றி உங்கள் கேள்வியை கேளுங்கள்', 'hi': 'मौसम के बारे में अपना प्रश्न पूछें' },
        'market': { 'en': 'Please ask your question about Market', 'ta': 'சந்தை பற்றி உங்கள் கேள்வியை கேளுங்கள்', 'hi': 'बाजार के बारे में अपना प्रश्न पूछें' },
        'farming': { 'en': 'Please ask your question about Farming', 'ta': 'விவசாயம் பற்றி உங்கள் கேள்வியை கேளுங்கள்', 'hi': 'खेती के बारे में अपना प्रश्न पूछें' },
        'health': { 'en': 'Please ask your question about Health', 'ta': 'சுகாதாரம் பற்றி உங்கள் கேள்வியை கேளுங்கள்', 'hi': 'स्वास्थ्य के बारे में अपना प्रश्न पूछें' },
        'schemes': { 'en': 'Please ask your question about Schemes', 'ta': 'அரசு திட்டங்கள் பற்றி உங்கள் கேள்வியை கேளுங்கள்', 'hi': 'सरकारी योजनाओं के बारे में अपना प्रश्न पूछें' },
        'emergency': { 'en': 'Please ask your question about Emergency', 'ta': 'அவசரம் பற்றி உங்கள் கேள்வியை கேளுங்கள்', 'hi': 'आपातकाल के बारे में अपना प्रश्न पूछें' }
    };
    
    const prompt = domainPrompts[topic][currentLang] || domainPrompts[topic]['en'];
    addChatBubble("assistant", prompt);
}

// UI Helper: Chat Bubbles
function addChatBubble(sender, text, hasAudio = false, voicePath = '') {
    const chatHistory = document.getElementById('chat-history');
    const msgDiv = document.createElement('div');
    msgDiv.className = `bubble ${sender === 'user' ? 'user-bubble' : 'assistant-bubble'}`;
    
    msgDiv.innerHTML = text;
    
    if (hasAudio && voicePath) {
        const audioWrap = document.createElement('div');
        audioWrap.style.marginTop = '10px';
        const audio = document.createElement('audio');
        // Add cache buster just in case
        audio.src = voicePath.startsWith('/') ? voicePath : '/' + voicePath;
        audio.controls = true;
        audio.autoplay = true;
        audio.onplay = () => setUIState('SPEAKING');
        audio.onended = () => setUIState('IDLE');
        audio.style.width = '100%';
        audio.style.height = '30px';
        audioWrap.appendChild(audio);
        msgDiv.appendChild(audioWrap);
    }
    
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight; 
}

// UI Helper: State Visuals
function setUIState(state) {
    const statusLabel = document.getElementById('status-bar');
    const waveform = document.getElementById('waveform');
    const micBtn = document.getElementById('mic-btn');
    const micIcon = document.getElementById('mic-icon');

    if (state === 'LISTENING') {
        statusLabel.classList.add('visible');
        statusLabel.innerText = "Listening...";
        waveform.classList.add('active');
        micBtn.classList.add('pulse');
        micIcon.setAttribute('data-lucide', 'square');
    } else if (state === 'PROCESSING') {
        statusLabel.innerText = "Processing...";
        waveform.classList.remove('active');
        micBtn.classList.remove('pulse');
        micIcon.setAttribute('data-lucide', 'refresh-cw');
        micIcon.classList.add('spin');
    } else if (state === 'SPEAKING') {
        statusLabel.innerText = "Speaking...";
        statusLabel.classList.add('visible');
    } else {
        statusLabel.classList.remove('visible');
        statusLabel.innerText = "";
        waveform.classList.remove('active');
        micBtn.classList.remove('pulse');
        micIcon.setAttribute('data-lucide', 'mic');
        micIcon.classList.remove('spin');
    }
    lucide.createIcons();
}

// ==========================================
// FEATURE 1: LOCATION
// ==========================================
function getLocation() {
    const card = document.getElementById('location-btn'); 
    
    if (!navigator.geolocation) {
        console.warn("Geolocation not supported");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            userLat = pos.coords.latitude.toFixed(4);
            userLon = pos.coords.longitude.toFixed(4);
            
            if (card) {
                card.style.background = '#e8f5e9';
                card.querySelector('span').innerText = 'Location OK ✔';
                card.querySelector('span').style.color = '#1b5e20';
            }
            console.log("Location stored:", userLat, userLon);
        },
        (err) => {
            console.error("Location error:", err);
        }
    );
}

// ==========================================
// FEATURE 2: IMAGE UPLOAD
// ==========================================
function handleImageSelect() {
    const input = document.getElementById('imageInput');
    const previewBox = document.getElementById('image-preview-container');
    const previewImg = document.getElementById('image-preview');

    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewBox.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

async function uploadImage() {
    const input = document.getElementById('imageInput');
    const previewBox = document.getElementById('image-preview-container');
    
    const formData = new FormData();
    formData.append('image', input.files[0]);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        addChatBubble("assistant", `<b>AI Crop Diagnosis:</b> ${data.result}`);
        previewBox.style.display = 'none';
        input.value = '';
    } catch (err) {
        console.error(err);
        alert("Image upload failed.");
    }
}

// ==========================================
// FEATURE 3: VOICE LOGIC
// ==========================================
async function toggleVoice() {
    if (voiceActive) {
        stopRecording();
        return;
    }
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };
        
        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            processAudioLogic(blob);
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        voiceActive = true;
        setUIState('LISTENING');

        autoStopTimer = setTimeout(() => {
            if (mediaRecorder.state === 'recording') stopRecording();
        }, 5000);

    } catch (err) {
        console.error("Mic error:", err);
        alert("Microphone access required.");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        voiceActive = false;
        if (autoStopTimer) clearTimeout(autoStopTimer);
    }
}

async function processAudioLogic(audioBlob, textQuery = null) {
    setUIState('PROCESSING');
    
    const formData = new FormData();
    if (audioBlob) formData.append('audio', audioBlob, 'query.webm');
    if (textQuery) formData.append('text_query', textQuery); 
    
    formData.append('language', currentLang);
    formData.append('domain', selectedDomain);
    if (userLat) formData.append('lat', userLat);
    if (userLon) formData.append('lon', userLon);

    try {
        const response = await fetch('/process', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.text) addChatBubble("user", data.text);
        if (data.answer) addChatBubble("assistant", data.answer, true, data.voice);
        
    } catch (err) {
        console.error("Server error:", err);
        addChatBubble("assistant", "⚠️ Server error. Please try again.");
    } finally {
        if (!document.querySelector('audio[autoplay]')) {
            setUIState('IDLE');
        }
    }
}
