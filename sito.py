from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurazione dell'applicazione Flask
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kodland_users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inizializza le estensioni Flask
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modello per gli Utenti del sistema
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        # Imposta la password usando il metodo pbkdf2:sha256 per una migliore sicurezza
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        # Verifica se la password inserita corrisponde a quella hashata
        return check_password_hash(self.password_hash, password)

# Modello per tracciare le Attività degli Utenti
class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # Tipi: 'weather', 'quiz', 'login'
    description = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100))  # Campo per le attività meteo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazione con il modello User
    user = db.relationship('User', backref=db.backref('activities', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    # Carica l'utente dal database tramite ID
    return User.query.get(int(user_id))

# Inizializzazione del database
with app.app_context():
    db.create_all()

# Funzione di utilità per registrare le attività degli utenti
def add_activity(user, activity_type, description, city=None):
    activity = UserActivity(
        user_id=user.id,
        activity_type=activity_type,
        description=description,
        city=city
    )
    db.session.add(activity)
    db.session.commit()

# Database delle Domande Quiz - Sviluppo AI e Python
quiz_questions = [
    # Fondamenti di Python per l'Intelligenza Artificiale
    {"question": "Quale libreria Python è considerata il gold standard per il machine learning?", "options": ["NumPy", "scikit-learn", "Matplotlib", "Pandas"], "correct": 1},
    {"question": "Quale tipo di dati usa principalmente NumPy per le operazioni matematiche?", "options": ["Liste Python standard", "Array multidimensionali", "Dizionari", "Stringhe"], "correct": 1},
    {"question": "Quale libreria Python è più adatta per la manipolazione e analisi dei dati tabellari?", "options": ["SciPy", "Pandas", "Seaborn", "TensorFlow"], "correct": 1},
    {"question": "In Python, quale libreria è principalmente usata per le operazioni di algebra lineare e calcolo scientifico?", "options": ["Math", "NumPy", "Statistics", "Random"], "correct": 1},
    {"question": "Quale libreria Python è specializzata nella visualizzazione di dati?", "options": ["Scikit-learn", "Matplotlib", "Requests", "BeautifulSoup"], "correct": 1},
    
    # Fondamenti del Machine Learning
    {"question": "Che tipo di apprendimento usa dati etichettati per addestrare un modello?", "options": ["Apprendimento non supervisionato", "Apprendimento supervisionato", "Apprendimento per rinforzo", "Deep learning"], "correct": 1},
    {"question": "Quale algoritmo è comunemente usato per la classificazione binaria?", "options": ["K-Means", "Random Forest", "Linear Regression", "DBSCAN"], "correct": 1},
    {"question": "Nel machine learning, cosa significa 'overfitting'?", "options": ["Il modello è troppo semplice", "Il modello funziona bene su dati nuovi", "Il modello memorizza i dati di training", "Il modello è molto veloce"], "correct": 2},
    {"question": "Quale metrica è comunemente usata per valutare un modello di classificazione?", "options": ["Mean Squared Error", "Accuracy", "Blue Score", "Perplexity"], "correct": 1},
    {"question": "Cosa fa la normalizzazione dei dati in machine learning?", "options": ["Aumenta la dimensione dei dati", "Riduce l'errore", "Riduce l'intervallo dei valori", "Aumenta la velocità"], "correct": 2},
    
    # Deep Learning e Reti Neurali
    {"question": "Qual è l'unità base di una rete neurale artificiale?", "options": ["Nodo", "Perceptron", "Layer", "Bias"], "correct": 1},
    {"question": "Quale libreria Python è più popolare per il deep learning?", "options": ["NumPy", "TensorFlow", "Requests", "Matplotlib"], "correct": 1},
    {"question": "In una rete neurale, cosa fa la funzione di attivazione?", "options": ["Inizializza i pesi", "Determina se un neurone si attiva", "Calcola l'errore", "Aggiorna i parametri"], "correct": 1},
    {"question": "Quale tipo di rete neurale è particolarmente efficace per le immagini?", "options": ["RNN", "CNN", "LSTM", "Transformer"], "correct": 1},
    {"question": "Cosa significa 'backpropagation'?", "options": ["Propagazione avanti dei dati", "Calcolo del gradiente all'indietro", "Aggiornamento manuale dei pesi", "Divisione dei dati"], "correct": 1},
    {"question": "In una rete neurale, cosa rappresentano i pesi?", "options": ["I parametri che determinano l'importanza delle connessioni", "I dati di input", "Le funzioni di attivazione", "Il numero di neuroni"], "correct": 0},
    {"question": "Qual è il principale vantaggio di usare più layer in una rete neurale?", "options": ["Maggiore velocità", "Riduzione dell'overfitting", "Maggiore flessibilità", "Memoria ridotta"], "correct": 2},
    {"question": "Cosa fa il layer di dropout in una rete neurale?", "options": ["Aggiunge più neuroni", "Spegne casualmente alcuni neuroni", "Aumenta il learning rate", "Cambia la funzione di attivazione"], "correct": 1},
    {"question": "Quale problema risolvono le RNN (Recurrent Neural Networks)?", "options": ["Classificazione di immagini", "Elaborazione di sequenze temporali", "Riconoscimento vocale", "Tutti i precedenti"], "correct": 3},
    
    # Computer Vision
    {"question": "Quale libreria Python è specializzata nella computer vision?", "options": ["OpenCV", "Pandas", "Requests", "Flask"], "correct": 0},
    {"question": "Nel riconoscimento di immagini, cosa sono i 'features'?", "options": ["Le dimensioni dell'immagine", "Le caratteristiche distintive estratte", "Il colore dell'immagine", "La risoluzione"], "correct": 1},
    {"question": "Quale tecnica è comunemente usata per ridurre la dimensionalità dei dati di immagini?", "options": ["PCA", "K-Means", "Random Forest", "Linear Regression"], "correct": 0},
    {"question": "Cosa fa la convoluzione in una CNN?", "options": ["Riduce le dimensioni", "Estrae caratteristiche locali", "Aumenta il contrasto", "Migliora la risoluzione"], "correct": 1},
    
    # Elaborazione del Linguaggio Naturale (NLP)
    {"question": "Quale libreria Python è più usata per il NLP?", "options": ["NumPy", "NLTK", "Matplotlib", "Requests"], "correct": 1},
    {"question": "Cosa significa 'tokenizzazione' in NLP?", "options": ["Traduzione automatica", "Divisione del testo in unità più piccole", "Classificazione di testi", "Analisi dei sentimenti"], "correct": 1},
    {"question": "Quale modello è considerato un breakthrough nel NLP?", "options": ["Word2Vec", "Transformer", "CNN", "K-Means"], "correct": 1},
    {"question": "Cosa fa la tecnica 'Bag of Words'?", "options": ["Ordina le parole alfabeticamente", "Rappresenta il testo come un insieme di parole", "Traduce il testo", "Migliora la grammatica"], "correct": 1},
    {"question": "Cos'è l'analisi del sentiment?", "options": ["Analisi grammaticale", "Determinazione delle emozioni nel testo", "Traduzione automatica", "Riconoscimento vocale"], "correct": 1},
    
    # Data Science e Statistica Applicata
    {"question": "Quale statistica misura la dispersione dei dati rispetto alla media?", "options": ["Media", "Mediana", "Deviazione standard", "Moda"], "correct": 2},
    {"question": "Cosa fa la regressione lineare?", "options": ["Trova una relazione lineare tra variabili", "Classifica i dati", "Riduce la dimensionalità", "Clusterizza i dati"], "correct": 0},
    {"question": "Nel contesto AI, cosa significa 'feature engineering'?", "options": ["Progettare nuovi algoritmi", "Selezionare e trasformare le caratteristiche", "Aumentare la velocità", "Migliorare la visualizzazione"], "correct": 1},
    {"question": "Quale tecnica è usata per validare un modello di ML?", "options": ["Training set", "Test set", "Cross-validation", "Bias-variance tradeoff"], "correct": 2},
    {"question": "Cosa rappresenta la 'curva ROC'?", "options": ["La curva di apprendimento", "Il trade-off tra sensitivity e specificity", "La distribuzione dei dati", "L'accuratezza del modello"], "correct": 1},
    
    # Etica e Buone Pratiche dell'AI
    {"question": "Nel contesto AI, cosa significa 'bias'?", "options": ["Errore sistematico nei dati o modelli", "Velocità di calcolo", "Complessità dell'algoritmo", "Dimensione del dataset"], "correct": 0},
    {"question": "Qual è un principio fondamentale dell'AI responsabile?", "options": ["Massimizzare l'accuratezza", "Trasparenza e fairness", "Velocità di esecuzione", "Semplicità del codice"], "correct": 1},
    {"question": "Cosa rende un dataset 'equilibrato' per la classificazione?", "options": ["Uguale rappresentanza delle classi", "Grandi dimensioni", "Alta qualità", "Bassa complessità"], "correct": 0},
    
    # Argomenti Avanzati di AI
    {"question": "Cos'è il 'transfer learning'?", "options": ["Migliorare i pesi", "Riutilizzare modelli pre-addestrati", "Aumentare la velocità", "Ridurre l'overfitting"], "correct": 1},
    {"question": "Cosa fa l'algoritmo di gradient descent?", "options": ["Aggiorna i parametri per minimizzare l'errore", "Aumenta l'accuratezza", "Velocizza il training", "Riduce la complessità"], "correct": 0},
    {"question": "Quale tecnica è usata per ridurre l'overfitting?", "options": ["Aumentare i dati", "Regularizzazione", "Usare più features", "Aumentare la complessità"], "correct": 1},
    {"question": "Cosa distingue il deep learning dal machine learning tradizionale?", "options": ["Usa reti neurali profonde", "È più veloce", "Usa meno dati", "È più semplice"], "correct": 0},
    {"question": "Nel reinforcement learning, cosa rappresenta la 'reward function'?", "options": ["La velocità di apprendimento", "Il feedback per le azioni", "La complessità dell'ambiente", "Il tipo di algoritmo"], "correct": 1}
]

# Definizione delle Route dell'applicazione Flask
@app.route('/')
def starter():
    # Pagina di benvenuto iniziale
    return render_template('starter.html')

@app.route('/homepage')
@login_required
def homepage():
    # Dashboard principale per utenti autenticati
    return render_template('homepage.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validazione dei campi obbligatori
        if not email or not password:
            flash('Email e password sono richieste', 'error')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            # Registra l'attività di accesso dell'utente
            add_activity(user, 'login', 'Ha effettuato l\'accesso al sistema')
            flash('Accesso effettuato con successo!', 'success')
            return redirect(url_for('homepage'))
        else:
            flash('Email o password non corretti', 'error')
    
    return render_template('login.html')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        
        # Validazione dei dati inseriti dall'utente
        if not nickname or not email or not password or not confirm_password:
            flash('Tutti i campi sono richiesti', 'error')
            return redirect(url_for('registration'))
        
        # Verifica che le password coincidano
        if password != confirm_password:
            flash('Le password non corrispondono', 'error')
            return redirect(url_for('registration'))
        
        # Controllo lunghezza minima password
        if len(password) < 6:
            flash('La password deve essere di almeno 6 caratteri', 'error')
            return redirect(url_for('registration'))
        
        # Verifica se l'email è già registrata
        if User.query.filter_by(email=email).first():
            flash('Un utente con questa email esiste già', 'error')
            return redirect(url_for('registration'))
        
        # Verifica se il nickname è già in uso
        if User.query.filter_by(nickname=nickname).first():
            flash('Questo nickname è già in uso. Scegli un nickname diverso.', 'error')
            return redirect(url_for('registration'))
        
        # Crea il nuovo utente nel database
        new_user = User(nickname=nickname, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registrazione completata con successo! Ora puoi accedere.', 'success')
        return redirect(url_for('login'))
    
    return render_template('registration.html')

@app.route('/logout')
@login_required
def logout():
    # Disconnette l'utente dal sistema
    logout_user()
    flash('Logout effettuato con successo!', 'success')
    return redirect(url_for('starter'))

@app.route('/quiz')
@login_required
def quiz():
    # Registra l'accesso alla sezione quiz
    add_activity(current_user, 'quiz', 'Ha effettuato l\'accesso alla pagina Quiz')
    return render_template('quiz.html')

@app.route('/api/quiz/questions')
@login_required
def get_quiz_questions():
    # Restituisce 30 domande casuali per un quiz quasi infinito
    import random
    selected_questions = random.sample(quiz_questions, min(30, len(quiz_questions)))
    return jsonify(selected_questions)

@app.route('/api/quiz/submit', methods=['POST'])
@login_required
def submit_quiz():
    data = request.get_json()
    answers = data.get('answers', [])
    current_score = data.get('score', 0)
    
    # Aggiorna il punteggio totale dell'utente
    current_user.total_score += current_score
    db.session.commit()
    
    # Registra il completamento del quiz
    add_activity(current_user, 'quiz_completion', f'Ha completato un quiz con punteggio: {current_score} punti')
    
    return jsonify({
        'success': True,
        'total_score': current_user.total_score,
        'message': f'Quiz completato! Hai totalizzato {current_score} punti.'
    })

@app.route('/profile')
@login_required
def profile():
    # Ottiene le attività recenti dell'utente (ultime 10)
    activities = UserActivity.query.filter_by(user_id=current_user.id)\
        .order_by(UserActivity.created_at.desc())\
        .limit(10)\
        .all()
    
    # Converte gli orari UTC nel fuso orario di Roma (UTC+1)
    from datetime import timezone, timedelta
    rome_tz = timezone(timedelta(hours=1))
    for activity in activities:
        # Converte l'orario UTC in fuso di Roma
        activity.rome_time = activity.created_at.replace(tzinfo=timezone.utc).astimezone(rome_tz)
    
    return render_template('profile.html', activities=activities)

@app.route('/nickname-suggestions')
def nickname_suggestions():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    try:
        # Controlla nicknames esistenti che contengono la query
        existing_users = User.query.filter(User.nickname.ilike(f'%{query}%')).all()
        existing_nicknames = [user.nickname for user in existing_users]
        
        # Genera suggerimenti intelligenti basati sulla query
        suggestions = []
        base_name = query.lower()
        
        # Prefissi italiani naturali e comuni tra i giovani
        prefixes = ['Il', 'La', 'Un', 'Una', 'Re', 'Duca', 'Principe', 'Cavaliere', 'Mago']
        # Suffissi italiani/stile moderno più freschi
        suffixes = ['ita', 'style', 'fan', 'lover', 'boy', 'girl', 'man', 'team', 'club', 'rules', '96', '97', '98', '00', '01', '2024']
        
        # Genera suggerimenti creativi (massimo 10 tentativi)
        for i in range(10):
            suggestion = query
            
            if i < 3:
                # Aggiungi numeri (anni di nascita popolari)
                if i == 0:
                    suggestion += '96'  # Generazione X/Y
                elif i == 1:
                    suggestion += '00'  # Inizio 2000s
                else:
                    suggestion += '24'  # Anno corrente
            
            elif i < 6:
                # Aggiungi prefissi italiani
                prefix = prefixes[i % len(prefixes)]
                suggestion = f"{prefix}{query.title()}"
            
            elif i < 9:
                # Aggiungi suffissi alla moda
                suffix = suffixes[i % len(suffixes)]
                suggestion = f"{query.title()}{suffix}"
            
            else:
                # Varianti con underscore + numeri
                suggestion = f"{query}_{i-8}"
            
            # Aggiungi solo se il nickname non è già occupato
            if suggestion not in existing_nicknames:
                suggestions.append(suggestion)
                
            if len(suggestions) >= 5:
                break
        
        return jsonify(suggestions[:5])
    
    except Exception as e:
        return jsonify([])

@app.route('/city-suggestions')
@login_required
def city_suggestions():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])

    api_key = os.getenv('OPENWEATHER_API_KEY', '944bb7e7f1b371939b8a50fc65823036')

    try:
        # Ottiene suggerimenti di città dall'API OpenWeatherMap
        geo_url = f'http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=5&appid={api_key}'
        geo_response = requests.get(geo_url)
        geo_data = geo_response.json()

        if geo_response.status_code != 200:
            return jsonify([])

        suggestions = []
        for city in geo_data:
            country = city.get('country', '')
            state = city.get('state', '')
            city_name = city['name']

            # Formatta il nome per la visualizzazione
            if state and country:
                display_name = f"{city_name}, {state}, {country}"
            elif country:
                display_name = f"{city_name}, {country}"
            else:
                display_name = city_name

            suggestions.append({
                'name': city_name,
                'display': display_name,
                'country': country,
                'state': state
            })

        return jsonify(suggestions)

    except Exception as e:
        return jsonify([])

@app.route('/weather')
@login_required
def weather():
    city = request.args.get('city')
    if not city:
        return jsonify({'error': 'Città non specificata'})

    # Utilizza l'API OpenWeatherMap per le previsioni
    api_key = os.getenv('OPENWEATHER_API_KEY', '944bb7e7f1b371939b8a50fc65823036')
    base_url = 'http://api.openweathermap.org/data/2.5/forecast'

    try:
        # Ottiene prima le coordinate geografiche
        geo_url = f'http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}'
        geo_response = requests.get(geo_url)
        geo_data = geo_response.json()

        if not geo_data:
            return jsonify({'error': 'Città non trovata'})

        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']

        # Richiede previsioni a 5 giorni
        forecast_url = f'{base_url}?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=it'
        forecast_response = requests.get(forecast_url)
        forecast_data = forecast_response.json()

        if forecast_response.status_code != 200:
            return jsonify({'error': 'Errore nel recupero delle previsioni'})

        # Elabora le previsioni per 3 giorni
        forecast = []
        today = datetime.now().date()

        # Nomi italiani per giorni e mesi
        italian_days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        italian_months = ['GEN', 'FEB', 'MAR', 'APR', 'MAG', 'GIU', 'LUG', 'AGO', 'SET', 'OTT', 'NOV', 'DIC']

        for i in range(3):
            target_date = today + timedelta(days=i)
            day_forecasts = [item for item in forecast_data['list'] if datetime.fromtimestamp(item['dt']).date() == target_date]

            if day_forecasts:
                # Calcola temperature diurne e notturne
                temps = [item['main']['temp'] for item in day_forecasts]
                day_temp = max(temps)
                night_temp = min(temps)

                # Trova la condizione meteorologica più comune
                weather_conditions = [item['weather'][0]['description'] for item in day_forecasts]
                weather = max(set(weather_conditions), key=weather_conditions.count)

                # Crea stringa dettagliata della data
                target_datetime = datetime.combine(target_date, datetime.min.time())
                day_name = italian_days[target_datetime.weekday()]
                month_name = italian_months[target_date.month - 1]
                date_str = f"{day_name} {target_date.day} {month_name} {target_date.year}"
                
                # Aggiunge riferimenti semplici per compatibilità
                if i == 0:
                    date_str = f"Oggi - {date_str}"
                elif i == 1:
                    date_str = f"Domani - {date_str}"
                elif i == 2:
                    date_str = f"Dopodomani - {date_str}"

                forecast.append({
                    'date': date_str,
                    'weather': weather.capitalize(),
                    'day_temp': round(day_temp),
                    'night_temp': round(night_temp)
                })

        # Registra l'attività meteo dell'utente
        add_activity(current_user, 'weather', f'Ha consultato le previsioni meteo per {city.title()}', city)

        return jsonify({
            'city': city.title(),
            'forecast': forecast
        })

    except Exception as e:
        return jsonify({'error': f'Errore: {str(e)}'})

@app.route('/scoreboard')
@login_required
def scoreboard():
    # Ottiene tutti gli utenti ordinati per punteggio totale (decrescente)
    players = User.query.order_by(User.total_score.desc()).all()
    
    # Aggiunge l'ultima attività per ogni giocatore
    for player in players:
        last_activity = UserActivity.query.filter_by(user_id=player.id)\
            .order_by(UserActivity.created_at.desc())\
            .first()
        player.last_activity = last_activity.created_at if last_activity else None
    
    # Calcola statistiche generali
    players_count = len(players)
    max_score = max([p.total_score for p in players]) if players else 0
    average_score = round(sum([p.total_score for p in players]) / players_count) if players_count > 0 else 0
    
    return render_template('scoreboard.html',
                         players=players,
                         players_count=players_count,
                         max_score=max_score,
                         average_score=average_score)

if __name__ == '__main__':
    app.run(debug=True)