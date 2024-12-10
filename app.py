## NEW FINAL CODE
from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
import spacy
from collections import Counter
import random
from PyPDF2 import PdfReader
import logging
import time

app = Flask(__name__)
Bootstrap(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load English tokenizer, tagger, parser, NER, and word vectors
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise Exception("Please run 'python -m spacy download en_core_web_sm' to install the spaCy model.")

def generate_mcqs(text, num_questions=5):
    if not text:
        return []

    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]

    mcqs = []
    while len(mcqs) < num_questions and len(sentences) > 0:
        sentence = sentences.pop(random.randint(0, len(sentences) - 1))  # Randomly select a sentence
        sent_doc = nlp(sentence)

        # Identify key nouns, verbs, and adjectives to replace for creating the blank
        nouns = [token.text for token in sent_doc if token.pos_ == "NOUN"]
        verbs = [token.text for token in sent_doc if token.pos_ == "VERB"]
        adjectives = [token.text for token in sent_doc if token.pos_ == "ADJ"]
        
        # Choose a noun, verb, or adjective as the subject to replace
        subject = None
        if nouns:
            subject = random.choice(nouns)  # Prefer nouns as the main subject
        elif verbs:
            subject = random.choice(verbs)
        elif adjectives:
            subject = random.choice(adjectives)

        if not subject:
            continue  # Skip if no valid subject is found

        question_stem = sentence.replace(subject, "______")

        # Gather possible distractors (nouns, verbs, adjectives from the sentence)
        distractors = list(set(nouns + verbs + adjectives) - {subject})
        
        # Ensure we have enough distractors, fill with other words if necessary
        while len(distractors) < 3:
            distractors.extend([token.text for token in sent_doc if token.pos_ == "NOUN" and token.text != subject][:3 - len(distractors)])

        # Ensure we have exactly 4 options, including the correct answer
        options = [subject] + distractors[:3]
        random.shuffle(options)

        # Ensure the correct answer is in the list and form a choice letter (A, B, C, D)
        correct_answer = chr(64 + options.index(subject) + 1)
        mcqs.append((question_stem, options, correct_answer))

    return mcqs

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = ""

        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            for file in files:
                if file.filename.endswith('.pdf'):
                    text += process_pdf(file)
                elif file.filename.endswith('.txt'):
                    text += file.read().decode('utf-8')
        else:
            text = request.form.get('text', '')

        # Log the extracted text to check if it's correct
        logging.debug(f"Extracted text: {text[:500]}")  # Log the first 500 characters for review

        num_questions = int(request.form.get('num_questions', 5))
        mcqs = generate_mcqs(text, num_questions=num_questions)
        
        # Ensure the number of questions returned matches the requested number
        while len(mcqs) < num_questions:
            mcqs.append(("Not enough content to generate question.", [], ""))  # Placeholder if not enough valid content

        mcqs_with_index = [(i + 1, mcq) for i, mcq in enumerate(mcqs)]
        return render_template('mcqs.html', mcqs=mcqs_with_index, num_questions=num_questions)

    return render_template('index.html')

@app.route('/submit_answers', methods=['POST'])
def submit_answers():
    correct_answers = 0
    num_questions = int(request.form['num_questions'])

    for i in range(1, num_questions + 1):
        selected_answer = request.form.get(f"answer{i}")
        correct_answer = request.form.get(f"correct_answer{i}")
        
        if selected_answer == correct_answer:
            correct_answers += 1

    score = (correct_answers / num_questions) * 100
    return render_template('result.html', score=score, total=num_questions, correct_answers=correct_answers)

def process_pdf(file):
    text = ""
    try:
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:  # Only append text if it's extracted
                text += page_text
            else:
                logging.warning("No text extracted from page.")
    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
    return text

if __name__ == '__main__':
    app.run(debug=True)