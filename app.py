from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import sqlite3
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# Load environment variables from .env file
load_dotenv()

# Get API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Test the key
# print("OpenAI API Key Loaded:", bool(openai.api_key))  # Should print True if loaded

# Initialize database
conn = sqlite3.connect("essays.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS essays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        essay TEXT,
        feedback TEXT,
        clarity INT,
        argument INT,
        evidence INT,
        organization INT,
        grammar INT,
        style INT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# proofreading and feedback api

def analyze_essay(essay):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an essay writing teacher. Assess the essay based on clarity, argument, evidence, organization, grammar, and style."},
            {"role": "user", "content": essay}
        ]
    )
    return response["choices"][0]["message"]["content"]

# When a revised essay is submitted, wi'll compare it to the original feedback


# Root endpoint to check if the server is running
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Essay Writing Teacher Plugin is running!"})

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    essay = data.get("essay")

    if not essay:
        return jsonify({"error": "No essay provided"}), 400

    feedback = analyze_essay(essay)

    # Simulated scores (You can refine this with GPT's response parsing)
    scores = {
        "clarity": 17,
        "argument": 18,
        "evidence": 16,
        "organization": 19,
        "grammar": 15,
        "style": 16
    }

    # Store the essay and feedback
    cursor.execute("""
        INSERT INTO essays (essay, feedback, clarity, argument, evidence, organization, grammar, style)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (essay, feedback, scores["clarity"], scores["argument"], scores["evidence"], scores["organization"], scores["grammar"], scores["style"]))
    conn.commit()

    return jsonify({
        "feedback": feedback,
        "scores": scores
    })

@app.route("/resubmit/<int:essay_id>", methods=["POST"])
def resubmit(essay_id):
    data = request.json
    new_essay = data.get("essay")

    cursor.execute("SELECT essay FROM essays WHERE id=?", (essay_id,))
    original = cursor.fetchone()

    if not original:
        return jsonify({"error": "Original essay not found"}), 404

    # Analyze again
    feedback = analyze_essay(new_essay)

    return jsonify({
        "message": "Revised essay analyzed successfully!",
        "feedback": feedback
    })

# fetch past essays and summarize strengths and weaknesses

@app.route("/monthly_report", methods=["GET"])
def monthly_report():
    cursor.execute("""
        SELECT clarity, argument, evidence, organization, grammar, style FROM essays 
        WHERE submitted_at >= date('now', '-30 days')
    """)
    essays = cursor.fetchall()

    if not essays:
        return jsonify({"message": "No essays submitted this month"}), 200

    # Calculate averages
    categories = ["clarity", "argument", "evidence", "organization", "grammar", "style"]
    averages = {cat: sum(e[i] for e in essays) / len(essays) for i, cat in enumerate(categories)}

    # Personalized improvement suggestions
    report = f"""
    Your monthly writing report:
    - Strengths: {max(averages, key=averages.get)}.
    - Weakest area: {min(averages, key=averages.get)}.
    - Suggestions: Focus on improving {min(averages, key=averages.get)} by doing more structured outlines before writing.
    """

    return jsonify({"report": report, "averages": averages})


# Endpoint for submitting an essay
@app.route('/submit-essay', methods=['POST'])
def submit_essay():
    essay_text = request.json.get("essay_text")
    if not essay_text:
        return jsonify({"error": "No essay text provided"}), 400
    
    # Call the OpenAI API to process the essay
    feedback = generate_feedback(essay_text)
    
    return jsonify({"feedback": feedback})

def generate_feedback(essay_text):
    # You would integrate your essay feedback logic here
    # Example of calling OpenAI API for feedback
    response = openai.Completion.create(
        engine="text-davinci-003",  # Adjust this based on your preferred engine
        prompt=f"Proofread this essay and provide feedback: {essay_text}",
        max_tokens=500
    )
    return response.choices[0].text.strip()

if __name__ == "__main__":
    app.run(debug=True)
