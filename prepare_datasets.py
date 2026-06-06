"""
prepare_dataset.py  (v3 — CLINC150 via GitHub, no HuggingFace needed)
────────────────────────────────────────────────────────────────────────────────
Uses the CLINC150 dataset (150 intents, 22,500 utterances) downloaded directly
from GitHub. No HuggingFace, no auth, no version conflicts.

Why CLINC150:
  - Perfectly balanced (100 samples/intent in train)
  - 150 real-world intents across banking, travel, food, home, etc.
  - Human-written, English utterances
  - These become the ENGLISH base → next script merges with Hindi/Tamil
    word lists to build Hinglish/Tanglish code-switched data

Source: https://github.com/clinc/oos-eval (CC BY 3.0)

Run:
    python prepare_dataset.py          # no pip installs needed beyond stdlib

Output:
    data/clinc150_en.jsonl             — 22,500 English utterances, labelled
    data/clinc150_summary.txt          — intent list + per-domain breakdown
"""

import json
import urllib.request
from pathlib import Path
from collections import Counter, defaultdict

# ─── Config ──────────────────────────────────────────────────────────────────

CLINC150_URL = (
    "https://raw.githubusercontent.com/clinc/oos-eval/master/data/data_full.json"
)

OUTPUT_DIR = Path("data")

# Map CLINC150 intents to broader domains for our schema
# (CLINC150 doesn't have explicit domains, so we group them)
INTENT_TO_DOMAIN = {
    # Banking & Finance
    "balance": "banking", "transfer": "banking", "transactions": "banking",
    "pay_bill": "banking", "freeze_account": "banking", "pin_change": "banking",
    "bill_balance": "banking", "bill_due": "banking", "account_blocked": "banking",
    "min_payment": "banking", "interest_rate": "banking", "apr": "banking",
    "routing": "banking", "direct_deposit": "banking", "spending_history": "banking",
    "payday": "banking", "income": "banking", "order_checks": "banking",
    "redeem_rewards": "banking", "rewards_balance": "banking",
    "credit_limit": "banking", "credit_limit_change": "banking",
    "credit_score": "banking", "improve_credit_score": "banking",
    "new_card": "banking", "damaged_card": "banking", "card_declined": "banking",
    "report_lost_card": "banking", "replacement_card_duration": "banking",
    "expiration_date": "banking", "report_fraud": "banking",
    "rollover_401k": "banking", "w2": "banking", "taxes": "banking",
    # Travel
    "book_flight": "travel", "book_hotel": "travel", "car_rental": "travel",
    "flight_status": "travel", "lost_luggage": "travel", "travel_alert": "travel",
    "travel_notification": "travel", "travel_suggestion": "travel",
    "international_fees": "travel", "international_visa": "travel",
    "plug_type": "travel", "carry_on": "travel", "cancel_reservation": "travel",
    "confirm_reservation": "travel", "accept_reservations": "travel",
    "vaccines": "travel",
    # Food & Restaurants
    "restaurant_suggestion": "food", "restaurant_reviews": "food",
    "restaurant_reservation": "food", "recipe": "food", "meal_suggestion": "food",
    "food_last": "food", "ingredient_substitution": "food",
    "ingredients_list": "food", "nutrition_info": "food",
    "calories": "food", "cook_time": "food",
    # Smart Home & IoT
    "smart_home": "smart_home", "change_volume": "smart_home",
    "change_speed": "smart_home", "change_accent": "smart_home",
    "whisper_mode": "smart_home", "reset_settings": "smart_home",
    "sync_device": "smart_home",
    # Productivity & Calendar
    "calendar": "productivity", "calendar_update": "productivity",
    "schedule_meeting": "productivity", "meeting_schedule": "productivity",
    "reminder": "productivity", "reminder_update": "productivity",
    "todo_list": "productivity", "todo_list_update": "productivity",
    "shopping_list": "productivity", "shopping_list_update": "productivity",
    "pto_balance": "productivity", "pto_request": "productivity",
    "pto_request_status": "productivity", "pto_used": "productivity",
    # Transport & Navigation
    "directions": "transport", "distance": "transport", "traffic": "transport",
    "gas": "transport", "gas_type": "transport", "mpg": "transport",
    "uber": "transport", "current_location": "transport",
    "oil_change_when": "transport", "oil_change_how": "transport",
    "jump_start": "transport", "tire_change": "transport",
    "tire_pressure": "transport", "last_maintenance": "transport",
    "schedule_maintenance": "transport",
    # Music & Entertainment
    "play_music": "entertainment", "next_song": "entertainment",
    "update_playlist": "entertainment", "what_song": "entertainment",
    # Communication
    "make_call": "communication", "text": "communication",
    "share_location": "communication", "find_phone": "communication",
    # Information & General
    "weather": "general", "time": "general", "date": "general",
    "timer": "general", "alarm": "general", "definition": "general",
    "translate": "general", "spelling": "general", "measurement_conversion": "general",
    "exchange_rate": "general", "timezone": "general",
    "next_holiday": "general", "calculator": "general",
    "flip_coin": "general", "roll_dice": "general",
    "fun_fact": "general", "tell_joke": "general",
    "meaning_of_life": "general", "how_busy": "general",
    # Shopping
    "order": "shopping", "order_status": "shopping", "cancel": "shopping",
    # Insurance & Healthcare
    "insurance": "insurance", "insurance_change": "insurance",
    # Meta / Bot interaction
    "greeting": "meta", "goodbye": "meta", "thank_you": "meta",
    "yes": "meta", "no": "meta", "maybe": "meta", "repeat": "meta",
    "are_you_a_bot": "meta", "what_are_your_hobbies": "meta",
    "how_old_are_you": "meta", "do_you_have_pets": "meta",
    "what_is_your_name": "meta", "change_ai_name": "meta",
    "what_can_i_ask_you": "meta", "who_made_you": "meta",
    "who_do_you_work_for": "meta", "where_are_you_from": "meta",
    "user_name": "meta", "change_user_name": "meta",
    "change_language": "meta", "application_status": "meta",
}


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 65)
    print("  CLINC150 Dataset Downloader")
    print("  Source: github.com/clinc/oos-eval")
    print("  150 intents | 22,500 utterances | perfectly balanced")
    print("═" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Download ─────────────────────────────────────────────────────────────
    print(f"\n  Downloading from GitHub...", end=" ", flush=True)
    try:
        with urllib.request.urlopen(CLINC150_URL, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        print("✓")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return

    # ── Parse ─────────────────────────────────────────────────────────────────
    rows = []
    split_map = {"train": "train", "val": "validation", "test": "test"}

    for src_split, our_split in split_map.items():
        for text, intent in data[src_split]:
            rows.append({
                "text":         text.strip(),
                "intent":       intent,
                "domain":       INTENT_TO_DOMAIN.get(intent, "other"),
                "language_mix": "english",
                "split":        our_split,
            })

    # ── Write JSONL ───────────────────────────────────────────────────────────
    out_path = OUTPUT_DIR / "clinc150_en.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  Written: {out_path}  ({len(rows):,} rows)")

    # ── Summary ───────────────────────────────────────────────────────────────
    by_split  = Counter(r["split"]  for r in rows)
    by_domain = Counter(r["domain"] for r in rows)
    by_intent = Counter(r["intent"] for r in rows)
    domain_intents: dict = defaultdict(set)
    for r in rows:
        domain_intents[r["domain"]].add(r["intent"])

    print("\n" + "═" * 65)
    print("  DATASET SUMMARY")
    print("═" * 65)
    print(f"\n  Split counts:")
    for split, count in sorted(by_split.items()):
        print(f"    {split:<12} {count:>6,}")
    print(f"    {'TOTAL':<12} {len(rows):>6,}")

    print(f"\n  {'Domain':<16} {'Samples':>8}  {'# Intents':>10}  Intents")
    print(f"  {'-'*16} {'-'*8}  {'-'*10}  {'-'*35}")
    for domain, count in sorted(by_domain.items(), key=lambda x: -x[1]):
        intents = sorted(domain_intents[domain])
        n = len(intents)
        intent_str = ", ".join(intents[:5])
        if n > 5:
            intent_str += f" ... (+{n-5} more)"
        print(f"  {domain:<16} {count:>8,}  {n:>10}  {intent_str}")

    print(f"\n  Total unique intents : {len(by_intent)}")
    print(f"  Total unique domains : {len(by_domain)}")
    samples_per_intent = list(Counter(
        r["intent"] for r in rows if r["split"] == "train"
    ).values())
    print(f"  Samples/intent (train): min={min(samples_per_intent)}, "
          f"max={max(samples_per_intent)}, avg={sum(samples_per_intent)/len(samples_per_intent):.0f}")

    # ── Write summary text file ───────────────────────────────────────────────
    summary_path = OUTPUT_DIR / "clinc150_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("CLINC150 Intent → Domain Mapping\n")
        f.write("=" * 50 + "\n\n")
        for domain, intents in sorted(domain_intents.items()):
            f.write(f"[{domain}]\n")
            for intent in sorted(intents):
                f.write(f"  {intent}\n")
            f.write("\n")
    print(f"\n  Intent list saved: {summary_path}")
    print("═" * 65)
    print("\n  Next step → run build_codeswitched.py\n")


if __name__ == "__main__":
    main()