import json
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response

app = Flask(__name__, template_folder='frontend', static_folder='frontend')

users = []

FAST_API_BASE_URL="https://chilly-bunny-glazer-8136d184.koyeb.app"

@app.route('/')
def home():
    return render_template('welcome.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user_data = {
            "email": email,
            "password": password
        }

        try:
            response = requests.post(f"{FAST_API_BASE_URL}/api/v1/users/login", json=user_data)
            response.raise_for_status()
            response_data = response.json()

            token = response_data.get('access_token')
            user_info = response_data.get('user_info')

            if token and user_info:
                resp = make_response(jsonify({
                    "success": True,
                    "redirect": url_for('index')
                }))
                resp.set_cookie('access_token', token)
                resp.set_cookie('user_info', jsonify(user_info).data.decode('utf-8'))
                return resp
            else:
                return jsonify({"error": "Login failed!"}), 401
                
        except requests.exceptions.HTTPError as err:
            return jsonify({"error": str(err)}), response.status_code
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
@app.route('/index')
def index():
    token = request.cookies.get('access_token')
    if not token:
        return redirect(url_for('login'))
    
    return render_template('index.html')

import requests
from flask import render_template, request, redirect, url_for, jsonify

@app.route('/info', methods=['GET'])
def info():
    token = request.cookies.get('access_token')
    if not token:
        return redirect(url_for('login'))

    user_info = json.loads(request.cookies.get('user_info'))
    user_id = user_info.get('user_id')

    # Fetch user profile data from the API
    api_url = f"{FAST_API_BASE_URL}/api/v1/users/profile/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        user_profile = response.json()
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

    return render_template('card.html', user_profile=user_profile)


@app.route('/question', methods=['GET'])
def question():
    token = request.cookies.get('access_token')
    if not token:
        return redirect(url_for('login'))

    user_info = json.loads(request.cookies.get('user_info'))
    user_id = user_info.get('user_id')

    api_url = f"{FAST_API_BASE_URL}/api/v1/users/profile/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        user_profile = response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error fetching user profile: {e}")
        return jsonify({"error": "Failed to fetch user profile. Please try again later."}), 500

    current_role = user_profile.get('current_role')
    quiz_api_url = f"{FAST_API_BASE_URL}/api/v1/quiz/generate"
    payload = {"role": current_role}

    try:
        quiz_response = requests.post(quiz_api_url, json=payload, headers=headers, timeout=120)
        quiz_response.raise_for_status()
        quiz_data = quiz_response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error fetching quiz data: {e}")
        return jsonify({"error": "Failed to fetch quiz data. Please try again later."}), 500

    # Prepare the questions data
    questions = quiz_data['questions']
    for i, question in enumerate(questions, 1):
        question['number'] = i

    # Extract correct answers
    correct_answers = [q['answer'] for q in questions]

    # Pass the data to the template
    return render_template('question.html', questions=questions, new_role=quiz_data['role'], correct_answers=correct_answers)

@app.route('/evaluate', methods=['POST'])
def evaluate():
    token = request.cookies.get('access_token')
    if not token:
        return redirect(url_for('login'))

    user_info = json.loads(request.cookies.get('user_info'))
    user_id = user_info.get('user_id')

    request_data = request.json
    answers = request_data.get('answers')
    correct_answers = request_data.get('correct_answers')
    new_role = request_data.get('new_role')

    evaluate_api_url = f"{FAST_API_BASE_URL}/api/v1/quiz/evaluate-quiz/{user_id}"
    payload = {
        "answers": answers,
        "correct_answers": correct_answers,
        "new_role": new_role
    }

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(evaluate_api_url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error evaluating quiz: {e}")
        return jsonify({"error": "Failed to evaluate quiz. Please try again later."}), 500

    return jsonify(result)



@app.route('/ada-question', methods=['GET'])
def ada_ask_question():
    token = request.cookies.get('access_token')
    if not token:
        return redirect(url_for('login'))

    user_info = json.loads(request.cookies.get('user_info'))
    user_id = user_info.get('user_id')

    # Generate question
    generate_api_url = f"{FAST_API_BASE_URL}/api/v1/questions/generate/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(generate_api_url, headers=headers, timeout=120)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error generating question: {e}")
        return jsonify({"error": "Failed to generate questions. Please try again later."}), 500

    if result.get("message") == "User already has a role. No questions generated.":
        return redirect(url_for('index'))

    if result.get("message") == "Error contacting Flask API":
        # Update role and redirect to index
        update_role_api_url = f"{FAST_API_BASE_URL}/api/v1/questions/update_role/{user_id}"
        try:
            response = requests.post(update_role_api_url, headers=headers)
            response.raise_for_status()
            result = response.json()
        except requests.RequestException as e:
            app.logger.error(f"Error updating role: {e}")
            return jsonify({"error": "Failed to update user role. Please try again later."}), 500

        return jsonify({
            "popup_message": "Role upgraded successfully!",
            "redirect": url_for('index')
        })

    # Extract question data
    question_data = result.get('data')
    question_id = question_data.get('question_id')
    question_text = question_data.get('question_text')
    audio_file = question_data.get('audio_file')

    return render_template('checkRole.html', question_id=question_id, question_text=question_text, audio_file=audio_file)

@app.route('/answer', methods=['POST'])
def answer():
    token = request.cookies.get('access_token')
    if not token:
        return redirect(url_for('login'))

    user_info = json.loads(request.cookies.get('user_info'))
    user_id = user_info.get('user_id')
    
    data = request.get_json()
    question_id = data.get('question_id')
    user_audio = data.get('user_audio')  
    answer_api_url = f"{FAST_API_BASE_URL}/api/v1/questions/answer/{user_id}/{question_id}"

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(answer_api_url, json={"audio": user_audio}, headers=headers)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error submitting answer: {e}")
        return jsonify({"error": "Failed to submit answer. Please try again later."}), 500

    # Fetch next question
    return redirect(url_for('question'))

@app.route('/ask-ada', methods=['POST'])
def ask_ada():
    token = request.cookies.get('access_token')
    if not token:
        return redirect(url_for('login'))

    user_info = json.loads(request.cookies.get('user_info'))
    user_id = user_info.get('user_id')

    file = request.files.get('file')
    
    if not file:
        return render_template('index.html', user_id=user_id, error="No file uploaded.")

    files = {'file': (file.filename, file.read(), file.content_type)}

    try:
        # Fetch request ke Flask AI Service
        response = requests.post(f"{FAST_API_BASE_URL}/api/v1/chats/ask-ada/{user_id}", files=files, timeout=240)
        response.raise_for_status()

        # Parsing response JSON
        result = response.json()
        ada_response = result.get('ada_response')
        audio_file_url = result.get('audio_file')

        # Render template dengan hasil respons dari AI
        return render_template('index.html', user_id=user_id, ada_response=ada_response, audio_file_url=audio_file_url)

    except requests.exceptions.RequestException as e:
        # Render template dengan pesan error jika terjadi kesalahan
        return render_template('index.html', user_id=user_id, error=f"Failed to process and download audio: {str(e)}")

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.delete_cookie('access_token')
    resp.delete_cookie('user_info')
    return resp
