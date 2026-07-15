"""
run_agent.py

Full pipeline:
  1. Fetch recent emails from Gmail (read-only)
  2. Send each to Gemini for classification, scoring, and summarization
  3. Save enriched results to inbox_data.json for the dashboard

This script never sends, archives, deletes, or replies to anything.
"""

from gmail_reader import get_gmail_service, fetch_recent_emails
from ai_analyzer import analyze_batch
from storage import save_results


def run(max_results: int = 15):
    print("── Inbox Radar ─────────────────────────────")
    print("Connecting to Gmail (read-only)...")
    service = get_gmail_service()

    print(f"Fetching up to {max_results} emails...")
    raw_emails = fetch_recent_emails(service, max_results=max_results)
    print(f"Fetched {len(raw_emails)} emails.\n")

    print("Sending to Gemini for analysis...")
    processed = analyze_batch(raw_emails, delay=0.3)

    save_results(processed)

    # ── Print summary ────────────────────────────────────────────────
    print("\n── Results ─────────────────────────────────")
    for email in processed:
        imp = email.get("importance", 1)
        cat = email.get("category", "other").upper()
        flags = []
        if email.get("opportunity"):    flags.append("OPPORTUNITY")
        if email.get("action_needed"):  flags.append("ACTION NEEDED")
        if email.get("deadline"):       flags.append(f"DEADLINE: {email['deadline']}")
        flag_str = "  [" + " · ".join(flags) + "]" if flags else ""

        print(f"[{cat}] [{imp}/10] {email['subject'][:60]}{flag_str}")
        print(f"  {email['summary']}")
        print("-" * 60)

    by_cat = {}
    for e in processed:
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
    print(f"\nSaved {len(processed)} emails to inbox_data.json")
    print("  " + "  ".join(f"{k}: {v}" for k, v in sorted(by_cat.items())))


if __name__ == "__main__":
    run()
