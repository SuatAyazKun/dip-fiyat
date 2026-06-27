import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
with open('data/pending_deals.json', 'r', encoding='utf-8') as f:
    deals = json.load(f)
print(f'{len(deals)} firsat bulundu:')
for d in deals:
    print(f"  - {d['title'][:55]} | {d['current_price']} TL | %{d['discount_pct']}")
