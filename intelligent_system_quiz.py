from flask import Flask, render_template, request, session, redirect
import random
import json
import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'supersegretissima'

# Load questions once at startup
with open('domande.json', 'r', encoding='utf-8') as file:
    ALL_QUESTIONS = json.load(file)

@app.route('/', methods=['GET', 'POST'])
def welcome():
    """Schermata di benvenuto con impostazioni"""
    total_available = len([k for k in ALL_QUESTIONS.keys() if k.isdigit()])
    return render_template('welcome.html', total_available=total_available)

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    """Inizia il quiz con le impostazioni selezionate"""
    # Clear previous session
    session.clear()
    
    # Get settings from form
    duration = int(request.form.get('duration', 60))
    total_questions = int(request.form.get('total_questions', 40))
    mode = request.form.get('mode', 'exam')
    show_results = request.form.get('show_results', 'end')
    
    # Calculate dynamic questions per page based on total questions
    if total_questions <= 10:
        questions_per_page = total_questions  # Single page for 10 or fewer questions
    else:
        questions_per_page = 10  # Standard 10 questions per page for more than 10
    
    # Setup session
    chiavi = [k for k in ALL_QUESTIONS.keys() if k.isdigit()]
    available_questions = min(total_questions, len(chiavi))
    
    session['settings'] = {
        'duration': duration,
        'total_questions': available_questions,
        'questions_per_page': questions_per_page,
        'mode': mode,
        'show_results': show_results
    }
    
    session['scelte'] = random.sample(chiavi, available_questions)
    session['current_page'] = 1
    session['answers'] = {}  # Store all answers
    session['corrette'] = 0
    session['errate'] = 0
    
    # Setup timer
    if mode == 'exam' and duration > 0:
        session['start_time'] = time.time()
        session['end_time'] = time.time() + (duration * 60)
    
    return redirect('/quiz')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    """Pagina principale del quiz"""
    if 'settings' not in session:
        return redirect('/')
    
    settings = session['settings']
    
    # Handle form submission
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Save answers from current page
        for key, value in request.form.items():
            if key.startswith('q'):
                question_num = key[1:]  # Keep as string for JSON serialization
                session['answers'][question_num] = value
        
        # Handle navigation
        if action == 'next_page':
            session['current_page'] += 1
        elif action == 'prev_page':
            session['current_page'] -= 1
        elif action == 'goto_page':
            session['current_page'] = int(request.form.get('page', 1))
        elif action == 'goto_question':
            question_num = int(request.form.get('question', 1))
            # Calculate which page contains this question
            questions_per_page = settings['questions_per_page']
            target_page = ((question_num - 1) // questions_per_page) + 1
            session['current_page'] = target_page
        elif action == 'save_only':
            # Just save answers without navigation - return empty response
            return '', 204  # No Content response
        elif action == 'finish':
            # Check if all questions are answered - only count valid numeric answers
            valid_answers = {k: v for k, v in session['answers'].items() if k.isdigit()}
            unanswered_count = settings['total_questions'] - len(valid_answers)
            if unanswered_count > 0:
                # Don't allow finishing if there are unanswered questions
                pass  # Stay on current page
            else:
                return redirect('/results')
    
    # Check timer
    if settings['mode'] == 'exam' and 'end_time' in session:
        if time.time() >= session['end_time']:
            return redirect('/results')
    
    # Calculate pagination
    total_questions = settings['total_questions']
    questions_per_page = settings['questions_per_page']
    current_page = session['current_page']
    total_pages = (total_questions + questions_per_page - 1) // questions_per_page
    
    # Get questions for current page
    start_idx = (current_page - 1) * questions_per_page
    end_idx = min(start_idx + questions_per_page, total_questions)
    
    questions = []
    for i in range(start_idx, end_idx):
        chiave = session['scelte'][i]
        # Check if question still exists in the JSON file
        if chiave not in ALL_QUESTIONS:
            # Skip missing questions and continue
            continue
        domanda_data = ALL_QUESTIONS[chiave]
        
        question = {
            'number': i + 1,
            'chiave': chiave,
            'domanda': domanda_data['domanda'],
            'risposte': domanda_data['risposte'],
            'giusta': domanda_data['giusta'],
            'selected': session['answers'].get(str(i + 1)),
            'answered': str(i + 1) in session['answers'],
            'correct': None
        }
        
        # Check if answer is correct (for immediate feedback)
        if question['answered'] and settings['show_results'] == 'immediate':
            question['correct'] = question['selected'] == question['giusta']
        
        questions.append(question)
    
    # Calculate stats - only count numeric question keys
    valid_answers = {k: v for k, v in session['answers'].items() if k.isdigit()}
    answered_count = len(valid_answers)
    unanswered_count = total_questions - answered_count
    
    # Get answered question numbers as integers for template
    answered_questions = [int(q) for q in session['answers'].keys() if q.isdigit()]
    
    # Get current page question numbers
    current_page_questions = list(range(start_idx + 1, end_idx + 1))
    
    # Calculate time remaining
    time_remaining = ""
    time_remaining_seconds = 0
    if settings['mode'] == 'exam' and 'end_time' in session:
        remaining = session['end_time'] - time.time()
        if remaining > 0:
            time_remaining_seconds = int(remaining)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            if hours > 0:
                time_remaining = f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
            else:
                time_remaining = f"{int(minutes)}:{int(seconds):02d}"
        else:
            time_remaining = "00:00"
    
    return render_template('quiz.html',
                         questions=questions,
                         current_page=current_page,
                         total_pages=total_pages,
                         total_questions=total_questions,
                         answered=answered_count,
                         unanswered_count=unanswered_count,
                         answered_questions=answered_questions,
                         current_page_questions=current_page_questions,
                         corrette=session['corrette'],
                         errate=session['errate'],
                         mode=settings['mode'],
                         duration=settings['duration'],
                         show_results=settings['show_results'],
                         time_remaining=time_remaining,
                         time_remaining_seconds=time_remaining_seconds)

@app.route('/results')
def results():
    """Pagina dei risultati finali"""
    if 'settings' not in session:
        return redirect('/')
    
    settings = session['settings']
    
    # Calculate final score
    corrette = 0
    errate = 0
    detailed_results = []
    
    for i, chiave in enumerate(session['scelte']):
        question_num = i + 1
        # Check if question still exists in the JSON file
        if chiave not in ALL_QUESTIONS:
            # Skip missing questions and continue
            continue
        domanda_data = ALL_QUESTIONS[chiave]
        user_answer = session['answers'].get(str(question_num))
        correct_answer = domanda_data['giusta']
        is_correct = user_answer == correct_answer
        
        if user_answer:  # Only count answered questions
            if is_correct:
                corrette += 1
            else:
                errate += 1
        
        detailed_results.append({
            'number': question_num,
            'domanda': domanda_data['domanda'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'correct': is_correct
        })
    
    total_answered = corrette + errate
    score = round((corrette / total_answered * 100) if total_answered > 0 else 0)
    
    # Calculate time used
    tempo_impiegato = None
    if settings['mode'] == 'exam' and 'start_time' in session:
        time_used = time.time() - session['start_time']
        hours = int(time_used // 3600)
        minutes = int((time_used % 3600) // 60)
        seconds = int(time_used % 60)
        if hours > 0:
            tempo_impiegato = f"{hours}h {minutes}m {seconds}s"
        else:
            tempo_impiegato = f"{minutes}m {seconds}s"
    
    return render_template('results.html',
                         corrette=corrette,
                         errate=errate,
                         totale=len(session['scelte']),
                         score=score,
                         tempo_impiegato=tempo_impiegato,
                         detailed_results=detailed_results if settings['show_results'] == 'end' else None)

@app.route('/reset')
def reset():
    """Reset session and return to welcome"""
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)