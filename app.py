import os
import base64
import re
import time
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from google import genai
from google.genai import types
from PIL import Image
import pytesseract

app = Flask(__name__, template_folder='.')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

AI_PROMPT = """Transform the given classroom board image (and extracted OCR text if provided) into clean, well-structured, aesthetic handwritten-style study notes rendered as HTML.

STRICT INSTRUCTIONS:
- Preserve ALL important information from the board (do not omit key concepts, numbers, or relationships)
- Correct unclear or messy handwriting logically, but do not change intended meaning
- Fix OCR errors if present
- Rewrite content slightly for clarity and readability while keeping it concise

CORRECTNESS VERIFICATION (VERY IMPORTANT):
- Verify whether the extracted content is logically and academically correct
- If any part is clearly incorrect, fix it using correct subject knowledge
- Do NOT guess or hallucinate missing information
- If something is unclear or ambiguous, keep it neutral rather than inventing details
- Ensure formulas, values, and relationships are accurate

STRUCTURE:
- Add a clear main title at the top (based on the topic)
- Organize content into sections such as: Definition, Concept, Steps/Process, Properties, Example
- Use bullet points instead of long paragraphs
- Maintain logical flow and hierarchy

DIAGRAM HANDLING - VERY IMPORTANT:
If the board contains ANY diagram, graph, flowchart, tree, network, circuit, cycle, or visual structure, you MUST recreate it as a proper inline SVG element. Rules:
- Use <svg> tags with appropriate width, height and viewBox
- Draw actual shapes: <rect>, <circle>, <ellipse>, <line>, <path>, <polygon> for nodes/boxes/arrows
- Use <text> elements for all labels inside the SVG with font-family="Kalam, cursive"
- Use <defs> and <marker> for arrowheads on directed edges
- Use pastel fill colors: #cce5ff for regular nodes, #ccf5d6 for highlighted nodes, #ffd6e0 for special nodes, #fff3b0 for start/end nodes
- Draw edges/arrows between nodes precisely showing correct connections and edge weights
- Keep diagrams clean, symmetric, and well-spaced with generous padding
- Wrap each SVG in <div class="diagram-box"> with a <p class="diagram-caption"> label below
- For flowcharts: rectangles for process, diamonds for decisions, rounded-rect for start/end
- For trees/graphs: position nodes evenly, draw edges with weight labels midway
- For tables/matrices: use HTML <table class="notes-table"> with proper th and td
- NEVER use ASCII art or plain text to represent diagrams - always use real SVG shapes
- Make SVG width="100%" with a fixed viewBox so it scales responsively

ARROWHEAD PATTERN (always use this for directed graphs):
<defs><marker id="arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#4a90d9"/></marker></defs>
Then on lines: marker-end="url(#arr)"

STYLE (VERY IMPORTANT):
- Output should look like neat iPad handwritten notes (GoodNotes style)
- Use clean, structured HTML
- Use soft pastel highlights behind headings or important terms
- Keep spacing balanced and visually pleasing
- Maintain a minimal, academic aesthetic

OUTPUT FORMAT - RETURN ONLY HTML (no markdown, no code fences):
Return a single HTML fragment (no <html>, <head>, or <body> tags) containing:
- A <div class="notes-page"> wrapper
- A <h1 class="notes-title"> for the main topic
- Multiple <section class="notes-section"> blocks with:
  - <h2 class="section-heading" style="background: var(--highlight-yellow)"> for titles
  - <ul class="notes-list"> with <li> items
  - <div class="formula-box"> for formulas
  - <div class="diagram-box"><svg ...>...</svg><p class="diagram-caption">Caption</p></div> for diagrams
  - <table class="notes-table"> for tabular data
  - <span class="highlight-pink/yellow/green/blue"> for important terms
- A <div class="notes-footer"> at the end

GOAL: Create visually appealing, accurate notes with REAL SVG diagrams — not text art. Every diagram on the board must become a proper SVG drawing."""


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_ocr(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, config='--psm 6')
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        return text
    except Exception as e:
        return f"OCR extraction failed: {str(e)}"


def process_with_gemini(image_path, ocr_text, retry=0):
    if not GEMINI_API_KEY:
        return generate_demo_notes(ocr_text)

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        with open(image_path, 'rb') as f:
            image_data = f.read()

        ext = image_path.rsplit('.', 1)[1].lower()
        mime_map = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp'
        }
        mime_type = mime_map.get(ext, 'image/jpeg')

        full_prompt = AI_PROMPT
        if ocr_text and len(ocr_text) > 20:
            full_prompt += f"\n\nOCR EXTRACTED TEXT (for reference):\n{ocr_text}"

        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Gemini 2.5 Flash — fast, multimodal, vision-capable
            contents=[
                types.Part.from_bytes(data=image_data, mime_type=mime_type),
                types.Part.from_text(text=full_prompt),
            ]
        )

        html_output = response.text

        # Strip markdown code fences if present
        html_output = re.sub(r'^```html?\n?', '', html_output, flags=re.MULTILINE)
        html_output = re.sub(r'\n?```$', '', html_output, flags=re.MULTILINE)

        return html_output.strip()

    except Exception as e:
        error_str = str(e)

        # Handle rate limiting — retry once after delay, then try pro model
        if ('429' in error_str or 'RESOURCE_EXHAUSTED' in error_str) and retry < 2:
            if retry == 0:
                # First retry: wait briefly and try again with Flash
                time.sleep(15)
                return process_with_gemini(image_path, ocr_text, retry=1)
            else:
                # Second retry: upgrade to Pro model
                try:
                    client2 = genai.Client(api_key=GEMINI_API_KEY)
                    with open(image_path, 'rb') as f:
                        image_data2 = f.read()
                    ext2 = image_path.rsplit('.', 1)[1].lower()
                    mime_map2 = {'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','gif':'image/gif','webp':'image/webp','bmp':'image/bmp'}
                    mime_type2 = mime_map2.get(ext2, 'image/jpeg')
                    full_prompt2 = AI_PROMPT
                    if ocr_text and len(ocr_text) > 20:
                        full_prompt2 += f"\n\nOCR EXTRACTED TEXT (for reference):\n{ocr_text}"
                    response2 = client2.models.generate_content(
                        model='gemini-2.5-pro',  # Fallback to Pro
                        contents=[
                            types.Part.from_bytes(data=image_data2, mime_type=mime_type2),
                            types.Part.from_text(text=full_prompt2),
                        ]
                    )
                    html2 = response2.text
                    html2 = re.sub(r'^```html?\n?', '', html2, flags=re.MULTILINE)
                    html2 = re.sub(r'\n?```$', '', html2, flags=re.MULTILINE)
                    return html2.strip()
                except Exception:
                    pass  # Fall through to quota error message

        # Quota exhausted — helpful message
        if 'RESOURCE_EXHAUSTED' in error_str or '429' in error_str:
            return '''<div class="notes-page">
  <div class="error-box">
    <strong>⚠️ Gemini Free Tier Quota Exhausted</strong><br><br>
    Your daily free quota for Gemini 2.5 Flash has been used up.<br><br>
    <strong>Options to fix this:</strong>
    <ul style="margin-top:10px;line-height:2">
      <li>⏳ <strong>Wait</strong> — quota resets at midnight UTC</li>
      <li>💳 <strong>Enable billing</strong> at <a href="https://aistudio.google.com" target="_blank">aistudio.google.com</a> — costs ~₹0.01 per image</li>
      <li>🔑 <strong>Use a different Google account</strong> to get fresh free quota</li>
    </ul>
  </div>
</div>'''

        if 'API_KEY_INVALID' in error_str or 'invalid' in error_str.lower():
            return '<div class="notes-page"><div class="error-box"><strong>⚠️ Invalid API Key</strong><br>Your GEMINI_API_KEY appears to be incorrect. Get a free key at <a href="https://aistudio.google.com" target="_blank">aistudio.google.com</a>.</div></div>'

        return f'<div class="notes-page"><div class="error-box"><strong>⚠️ AI Processing Failed</strong><br>{error_str}<br><br>Please check your GEMINI_API_KEY in the .env file.</div></div>'


def generate_demo_notes(ocr_text):
    """Generate demo notes when no API key is set"""
    sample = ocr_text[:500] if ocr_text and len(ocr_text) > 20 else "Sample topic from board"
    return f"""<div class="notes-page">
  <div class="demo-banner">⚠️ Demo Mode — Set <code>GEMINI_API_KEY</code> in your <code>.env</code> file to enable AI-powered notes via <strong>Gemini 2.5 Flash</strong></div>
  <h1 class="notes-title">📝 Board Notes</h1>

  <section class="notes-section">
    <h2 class="section-heading" style="background: var(--highlight-yellow)">📌 Extracted Content</h2>
    <ul class="notes-list">
      <li>OCR successfully extracted text from your board image</li>
      <li>With a valid Gemini API key, this content will be structured into beautiful notes</li>
      <li>The AI will organize, correct, and format everything automatically</li>
    </ul>
  </section>

  <section class="notes-section">
    <h2 class="section-heading" style="background: var(--highlight-green)">🔍 Raw OCR Preview</h2>
    <div class="formula-box" style="white-space: pre-wrap; font-size: 0.85rem;">{sample[:300]}{"..." if len(sample) > 300 else ""}</div>
  </section>

  <section class="notes-section">
    <h2 class="section-heading" style="background: var(--highlight-blue)">⚙️ Setup Instructions</h2>
    <ul class="notes-list">
      <li>Get a free API key from <span class="highlight-pink">Google AI Studio (aistudio.google.com)</span></li>
      <li>Add it to your <code>.env</code> file: <code>GEMINI_API_KEY=your_key_here</code></li>
      <li>Restart the Flask server and upload your image again</li>
    </ul>
  </section>

  <div class="notes-footer">Generated by Smart Board Notes Generator</div>
</div>"""


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/static/style.css')
def style_css():
    return send_from_directory('.', 'style.css')


@app.route('/static/script.js')
def script_js():
    return send_from_directory('.', 'script.js')


@app.route('/process', methods=['POST'])
def process():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, BMP, or WEBP'}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Step 1: OCR
        ocr_text = extract_text_ocr(filepath)

        # Step 2: AI Processing with Gemini 2.5 Flash (auto-fallback to Pro)
        notes_html = process_with_gemini(filepath, ocr_text)

        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify({
            'success': True,
            'notes_html': notes_html,
            'ocr_text': ocr_text[:200] + '...' if len(ocr_text) > 200 else ocr_text
        })

    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/sample', methods=['POST'])
def sample():
    """Return sample notes to demonstrate the UI"""
    sample_html = """<div class="notes-page">
  <h1 class="notes-title">📐 Graph Theory — Shortest Path Algorithms</h1>

  <section class="notes-section">
    <h2 class="section-heading" style="background: var(--highlight-yellow)">📖 Definition</h2>
    <ul class="notes-list">
      <li>A <span class="highlight-yellow">Graph</span> is a set of <strong>vertices (nodes)</strong> connected by <strong>edges</strong></li>
      <li><span class="highlight-pink">Weighted Graph</span>: each edge has a numerical weight/cost</li>
      <li><span class="highlight-green">Shortest Path</span>: minimum total weight path between two vertices</li>
    </ul>
  </section>

  <section class="notes-section">
    <h2 class="section-heading" style="background: var(--highlight-pink)">⚡ Dijkstra's Algorithm</h2>
    <ul class="notes-list">
      <li>Finds shortest path from a <strong>source</strong> to all other vertices</li>
      <li>Works only with <span class="highlight-yellow">non-negative edge weights</span></li>
      <li>Uses a <strong>greedy approach</strong> with a priority queue</li>
    </ul>
    <div class="formula-box">Time Complexity: O((V + E) log V) &nbsp;|&nbsp; Space: O(V)</div>
  </section>

  <section class="notes-section">
    <h2 class="section-heading" style="background: var(--highlight-green)">🔢 Steps / Process</h2>
    <ul class="notes-list">
      <li><strong>Step 1:</strong> Initialize distance of source = 0, all others = ∞</li>
      <li><strong>Step 2:</strong> Add source to priority queue</li>
      <li><strong>Step 3:</strong> Extract vertex with minimum distance</li>
      <li><strong>Step 4:</strong> <span class="highlight-blue">Relax</span> all adjacent edges</li>
      <li><strong>Step 5:</strong> Repeat until queue is empty</li>
    </ul>
  </section>

  <div class="notes-footer">Generated by Smart Board Notes Generator ✨</div>
</div>"""
    return jsonify({'success': True, 'notes_html': sample_html, 'ocr_text': 'Sample demonstration'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
