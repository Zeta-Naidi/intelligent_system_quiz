from flask import Flask, render_template, request, session, redirect
import random
import json

app = Flask(__name__)
app.secret_key = 'supersegretissima'

@app.route('/', methods=['GET', 'POST'])
def quiz():
    with open('domande.json', 'r', encoding='utf-8') as file:
        tutte = json.load(file)

    if 'scelte' not in session:
        chiavi = [k for k in tutte.keys() if k.isdigit()]
        session['scelte'] = random.sample(chiavi, min(40, len(chiavi)))
        session['indice'] = 0
        session['corrette'] = 0
        session['errate'] = 0
        session['mostra_risultato'] = False

    selected = None
    corretto = None

    # Se arriva una risposta
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'rispondi':
            chiave = session['scelte'][session['indice']]
            selected = request.form.get('risposta')
            giusta = tutte[chiave]['giusta']
            corretto = (selected == giusta)
            if corretto:
                session['corrette'] += 1
            else:
                session['errate'] += 1
            session['mostra_risultato'] = True
        elif action == 'prossima':
            session['indice'] += 1
            session['mostra_risultato'] = False

    # Fine quiz
    if session['indice'] >= len(session['scelte']):
        return render_template('fine.html', corrette=session['corrette'], errate=session['errate'])

    chiave = session['scelte'][session['indice']]
    domanda_data = tutte[chiave]

    return render_template('domanda.html',
                           numero=session['indice'] + 1,
                           totale=len(session['scelte']),
                           corrette=session['corrette'],
                           errate=session['errate'],
                           domanda=domanda_data['domanda'],
                           risposte=domanda_data['risposte'],
                           chiave=chiave,
                           giusta=domanda_data['giusta'] if session.get('mostra_risultato') else None,
                           selezionata=selected,
                           corretto=corretto,
                           mostra_risultato=session.get('mostra_risultato', False))

@app.route('/reset')
def reset():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)