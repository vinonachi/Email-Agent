"""
ai_analyzer.py

Replaces classifier.py and summarizer.py entirely.

Uses Gemini 1.5 Flash (free tier) to analyze each email in a
single API call and return:

  - category        : interview | meeting | urgent | other
  - importance      : 1–10 integer
  - summary         : one short original sentence (12-20 words),
                      never a quote/paraphrase-lift from the email body
  - deadline        : detected date/time string, or null
  - opportunity     : true if this is a job offer, callback, or
                      career opportunity, false otherwise
  - action_needed   : true if the email explicitly asks the user
                      to do something, false otherwise

Setup
-----
1. Get a free API key from https://aistudio.google.com/app/apikey
2. Set it in your environment:
       export GEMINI_API_KEY="your_key_here"
   or paste it directly into GEMINI_API_KEY below (not recommended
   for code you share or commit).

Install
-------
    pip install google-generativeai
"""

import json
import os
import re
import time

import google.generativeai as genai

# ── API key ──────────────────────────────────────────────────────────
# Prefer environment variable; fall back to the string below.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-1.5-flash")

# ── Prompt template ──────────────────────────────────────────────────
_PROMPT = """
You are an intelligent email triage assistant.

Analyze the email below and respond with ONLY a valid JSON object —
no markdown fences, no extra text, no explanation.

Email details:
  Sender : {sender}
  Subject: {subject}
  Preview: {preview}

Return this exact JSON structure:
{{
  "category"      : "interview | meeting | urgent | other",
  "importance"    : <integer 1-10>,
  "summary"       : "<ONE short original sentence, 12-20 words, in your own words>",
  "deadline"      : "<detected date or time string, e.g. 'Thursday 3 PM', '06 May 2025', or null if none>",
  "opportunity"   : <true if this is a job offer, interview invite, callback, or career opportunity — false otherwise>,
  "action_needed" : <true if the email explicitly asks the reader to do something — false otherwise>
}}

Rules for "summary":
  - Write ONE plain sentence describing what the email is about and what
    (if anything) the reader needs to do.
  - Do NOT quote or copy phrases directly from the email body or subject.
  - Do NOT restate the date/time/deadline in the summary — that belongs
    only in the "deadline" field, never repeat it here.
  - Do NOT prefix it with the sender's name or "This email..." — just
    state the point directly.
  - Keep it to 12-20 words. No run-on sentences, no lists, no colons.

Good summary example:
  "Invitation to a virtual technical interview for the Associate
   Software Developer role."
Bad summary example (do not do this):
  "Vinothini N sent an interview email: 'Stradegi Solutions - Interview
   Invite'. Dear Candidate, kindly find below... Detected details: ..."

Scoring guide for importance (1–10):
  9–10  Interview invite, job offer, urgent deadline today
  7–8   Meeting request, follow-up requiring a reply, action due soon
  5–6   Informational update that may matter later
  3–4   Newsletter, general notification, automated alert
  1–2   Promotional, spam-like, or irrelevant
""".strip()

# ── Fallback when the API fails ──────────────────────────────────────
_FALLBACK = {
    "category": "other",
    "importance": 1,
    "summary": "Could not analyze this email.",
    "deadline": None,
    "opportunity": False,
    "action_needed": False,
}


def _clean_json(text: str) -> str:
    """Strip markdown fences if the model adds them despite instructions."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def analyze_email(sender: str, subject: str, preview: str) -> dict:
    """
    Send one email to Gemini and return a dict with the fields above.
    Falls back to _FALLBACK on any error so the pipeline never crashes.
    """
    prompt = _PROMPT.format(
        sender=sender or "(unknown)",
        subject=subject or "(no subject)",
        preview=preview or "(no preview)",
    )

    try:
        response = _model.generate_content(prompt)
        raw = _clean_json(response.text)
        result = json.loads(raw)

        # Normalise and validate fields
        result["category"] = result.get("category", "other").lower()
        if result["category"] not in ("interview", "meeting", "urgent", "other"):
            result["category"] = "other"

        result["importance"] = max(1, min(10, int(result.get("importance", 1))))

        summary = str(result.get("summary", "")).strip() or _FALLBACK["summary"]
        summary = summary.strip('"').strip("'")
        words = summary.split()
        if len(words) > 28:
            summary = " ".join(words[:28]).rstrip(",.;:") + "…"
        result["summary"] = summary

        result["deadline"] = result.get("deadline") or None
        result["opportunity"] = bool(result.get("opportunity", False))
        result["action_needed"] = bool(result.get("action_needed", False))

        return result

    except Exception as e:
        print(f"  [ai_analyzer] Gemini error for '{subject}': {e}")
        return dict(_FALLBACK)


def analyze_batch(emails: list[dict], delay: float = 0.3) -> list[dict]:
    """
    Analyze a list of email dicts (each must have sender_name,
    sender_email, subject, preview) and return each dict enriched
    with the Gemini fields.

    delay  — seconds to wait between calls to stay within free-tier
              rate limits (15 requests/min on the free plan).
    """
    results = []
    total = len(emails)

    for i, email in enumerate(emails, 1):
        print(f"  Analyzing {i}/{total}: {email.get('subject', '')[:60]}")
        analysis = analyze_email(
            sender=email.get("sender_name") or email.get("sender_email", ""),
            subject=email.get("subject", ""),
            preview=email.get("preview", ""),
        )
        enriched = {**email, **analysis}
        results.append(enriched)

        if i < total:
            time.sleep(delay)

    return results