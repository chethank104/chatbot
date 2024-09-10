from flask import Flask, render_template, request, jsonify
from responses import predefined_responses  # Import predefined responses from responses.py
import speech_recognition as sr
import sqlite3
from datetime import datetime, timedelta
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from fuzzywuzzy import fuzz

app = Flask(__name__)

# Database initialization
conn = sqlite3.connect('chat_history.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions
             (timestamp TEXT, user_message TEXT, bot_response TEXT)''')
conn.commit()

# Download NLTK resources
nltk.download('punkt')
nltk.download('stopwords')


def preprocess_message(message):
    stop_words = set(stopwords.words('english'))  # Define stopwords
    word_tokens = word_tokenize(message.lower())  # Tokenize and convert to lowercase
    filtered_tokens = [word for word in word_tokens if word not in stop_words]  # Remove stopwords
    return filtered_tokens

def get_bot_response(user_message, lang='en'):
    responses = predefined_responses.get(lang, {})
    user_tokens = preprocess_message(user_message)
    matched_responses = []
    
    for key in responses:
        # Tokenize and preprocess predefined response keywords
        response_tokens = preprocess_message(key)
        
        # Check similarity between user tokens and response tokens
        similarity_score = max(fuzz.token_set_ratio(user_tokens, response_tokens), 
                               fuzz.token_set_ratio(response_tokens, user_tokens))
        
        if similarity_score > 70:  # Adjust the threshold as needed
            matched_responses.append(responses[key])
    
    return matched_responses[0] if matched_responses else "I'm sorry, I didn't understand that. Can you please rephrase?"
def recognize_speech():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=15)  # Increase the listening time to 15 seconds
        
    try:
        query = recognizer.recognize_google(audio)
        return query
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand that."
    except sr.RequestError:
        return "Sorry, there was an error processing your request."

def save_chat_session(user_message, bot_response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chat_sessions (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
              (timestamp, user_message, bot_response))
    conn.commit()

def get_chat_sessions():
    seven_days_ago = datetime.now() - timedelta(days=7)
    c.execute("SELECT * FROM chat_sessions WHERE timestamp >= ?", (seven_days_ago.strftime("%Y-%m-%d %H:%M:%S"),))
    return c.fetchall()

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.form['user_message']
    lang = request.form.get('lang', 'en')  # Get language from the request, default to English
    bot_response = get_bot_response(user_message, lang)
    save_chat_session(user_message, bot_response)
    return jsonify({'bot_response': bot_response})

@app.route('/voice_message', methods=['POST'])
def voice_message():
    query = recognize_speech()
    bot_response = get_bot_response(query)
    save_chat_session(query, bot_response)
    return jsonify({'bot_response': bot_response})

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/chat_history', methods=['GET'])
def chat_history():
    chat_sessions = get_chat_sessions()
    return render_template('chat_history.html', chat_sessions=chat_sessions)

if __name__ == '__main__':
    app.run(debug=True)
