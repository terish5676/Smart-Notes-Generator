# 📒 Smart Notes Generator

Transform any image into beautiful, structured study notes using AI.

---

## ✨ Features

* **Image to Notes** — upload classroom board photos, handwritten pages, slides, screenshots, or documents
* **OCR text extraction** for cleaner AI processing
* **AI-powered note generation** using Gemini AI
* **Clean structured notes** with headings, summaries, bullet points, and highlighted concepts
* **SVG diagram rendering** for flowcharts, trees, and graphs
* **PDF download** support
* **Copy notes** to clipboard instantly
* **Raw OCR preview** panel
* **Dark mode** support with saved preferences
* **Sample notes** for quick testing
* **Mobile responsive** interface

---

## 🚀 Quick Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 2. Get a Gemini API key

1. Open url Google AI Studio[https://aistudio.google.com/](https://aistudio.google.com/)
2. Create an API key
3. Copy the generated key

---

### 3. Configure environment variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

---

### 4. Run the project

```bash
python app.py
```

Open in your browser:

```text
http://localhost:5000
```

---

## 📁 Project Structure

```text
smart-note-generator/
├── app.py
├── requirements.txt
├── .env
├── templates/
│   └── index.html
└── static/
    ├── style.css
    ├── script.js
    └── uploads/
```

---

## 🧠 How It Works

```text
Image Upload → OCR Extraction → Gemini AI Processing
→ Structured Notes → Download / Copy
```

Supports:

* Classroom board images
* Handwritten notes
* Screenshots
* Study materials
* Presentation slides
* Documents

---

## 🔧 Troubleshooting

| Problem              | Fix                                      |
| -------------------- | ---------------------------------------- |
| AI processing failed | Check your API key in `.env`             |
| Invalid API key      | Generate a new key from Google AI Studio |
| Image upload failed  | Use PNG, JPG, WEBP, GIF, or BMP          |
| Notes not generating | Refresh and try again                    |

---

## 📌 Notes

* Keep your `.env` file private
* Large images may take longer to process
* Best results come from clear, high-quality images
