import requests
import json
import time
from datetime import datetime
import os

"""
PoE2 Trade API - Session-Based Scraper
Scrape in multiple sessions with progress tracking
Resume where you left off!
"""

# API endpoints
SEARCH_API = "https://www.pathofexile.com/api/trade2/search/poe2/Standard"
FETCH_API = "https://www.pathofexile.com/api/trade2/fetch/"

# Configuration
ITEMS_PER_FETCH = 10
DELAY_BETWEEN_FETCHES = 5   # Increased to avoid rate limits
DELAY_BETWEEN_SEARCHES = 10  # Increased to avoid rate limits
OUTPUT_DIR = "poe2_session_dump"
PROGRESS_FILE = f"{OUTPUT_DIR}/progress.json"

def create_output_directory():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def save_progress(completed_categories, seen_item_ids):
    """Save progress so we can resume later"""
    progress = {
        'completed_categories': list(completed_categories),
        'seen_item_ids': list(seen_item_ids),
        'last_updated': datetime.now().isoformat()
    }
    
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def load_progress():
    """Load previous progress"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
            return set(progress['completed_categories']), set(progress['seen_item_ids'])
    return set(), set()

def search_items_with_filters(filters_dict, search_name=""):
    """Search for items with specific filters"""
    query = {
        "query": {
            "status": {
                "option": "any"
            }
        },
        "sort": {
            "price": "asc"
        }
    }
    
    query["query"].update(filters_dict)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.post(SEARCH_API, json=query, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            result = data.get('result', [])
            query_id = data.get('id', '')
            return result, query_id, total
        elif response.status_code == 429:
            print(f"  ⚠ Rate limited on search! Waiting 60 seconds...")
            time.sleep(60)
            return search_items_with_filters(filters_dict, search_name)
        else:
            print(f"  ✗ Search error: {response.status_code}")
            return [], '', 0
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return [], '', 0

def fetch_items_batch(item_ids, query_id):
    """Fetch a batch of items with retry logic"""
    if not item_ids:
        return None
    
    item_ids_str = ','.join(item_ids[:ITEMS_PER_FETCH])
    url = f"{FETCH_API}{item_ids_str}?query={query_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print("  ⚠ Rate limited! Waiting 60 seconds...")
            time.sleep(60)
            return fetch_items_batch(item_ids, query_id)
        else:
            return None
    except Exception as e:
        print(f"  ✗ Fetch exception: {e}")
        return None

def scrape_category(category_name, filters, subdivide_if_full=True):
    """Scrape a single category: SEARCH → FETCH → SAVE"""
    print(f"\n[SEARCH] {category_name}")
    
    item_ids, query_id, total = search_items_with_filters(filters, category_name)
    
    if not item_ids:
        print(f"  ✗ No items found")
        return []
    
    print(f"  ✓ Found {total:,} total, retrieved {len(item_ids)} IDs")
    
    # Check if we hit the 100 ID limit and there are more items
    if len(item_ids) >= 100 and total > 100 and subdivide_if_full:
        print(f"  ⚠ Hit 100 ID limit! Subdividing category to get more items...")
        return scrape_with_subdivision(category_name, filters, total)
    
    all_items = []
    num_batches = (len(item_ids) + ITEMS_PER_FETCH - 1) // ITEMS_PER_FETCH
    
    print(f"[FETCH] Fetching {len(item_ids)} items in {num_batches} batches...")
    
    for batch_num in range(num_batches):
        start_idx = batch_num * ITEMS_PER_FETCH
        end_idx = min(start_idx + ITEMS_PER_FETCH, len(item_ids))
        batch_ids = item_ids[start_idx:end_idx]
        
        batch_data = fetch_items_batch(batch_ids, query_id)
        
        if batch_data and batch_data.get('result'):
            items = batch_data['result']
            all_items.extend(items)
        
        if batch_num < num_batches - 1:
            time.sleep(DELAY_BETWEEN_FETCHES)
    
    # SAVE
    if all_items:
        safe_name = category_name.replace(" ", "_").replace("|", "-").replace("/", "-").replace(":", "")
        filename = f"{OUTPUT_DIR}/{safe_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'category': category_name,
                    'total_items': len(all_items),
                    'scrape_date': datetime.now().isoformat(),
                },
                'items': all_items
            }, f, indent=2, ensure_ascii=False)
        
        print(f"[SAVE] ✓ Saved {len(all_items)} items to {filename}")
    
    return all_items

def scrape_with_subdivision(category_name, filters, total_items):
    """Subdivide a category using item level ranges to get more than 100 items"""
    print(f"  → Subdividing by item level ranges...")
    
    # Define item level ranges for subdivision
    level_ranges = [
        (1, 20), (21, 40), (41, 50), (51, 60), (61, 65),
        (66, 70), (71, 75), (76, 80), (81, 85), (86, 100)
    ]
    
    all_items_combined = []
    
    for min_ilvl, max_ilvl in level_ranges:
        sub_filters = json.loads(json.dumps(filters))  # Deep copy
        
        # Add item level filter
        if "filters" not in sub_filters:
            sub_filters["filters"] = {}
        if "misc_filters" not in sub_filters["filters"]:
            sub_filters["filters"]["misc_filters"] = {"filters": {}}
        
        sub_filters["filters"]["misc_filters"]["filters"]["ilvl"] = {
            "min": min_ilvl,
            "max": max_ilvl
        }
        
        sub_category = f"{category_name}_ilvl{min_ilvl}-{max_ilvl}"
        print(f"    → {sub_category}")
        
        # Scrape this subdivision (don't subdivide again to avoid infinite recursion)
        items = scrape_category(sub_category, sub_filters, subdivide_if_full=False)
        all_items_combined.extend(items)
        
        # Small delay between subdivisions
        time.sleep(2)
    
    print(f"  ✓ Subdivision complete: {len(all_items_combined)} items from {len(level_ranges)} ranges")
    
    # Save combined results
    if all_items_combined:
        safe_name = category_name.replace(" ", "_").replace("|", "-").replace("/", "-").replace(":", "")
        filename = f"{OUTPUT_DIR}/{safe_name}_COMBINED.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'category': category_name,
                    'total_items': len(all_items_combined),
                    'subdivided': True,
                    'scrape_date': datetime.now().isoformat(),
                },
                'items': all_items_combined
            }, f, indent=2, ensure_ascii=False)
        
        print(f"[SAVE] ✓ Saved {len(all_items_combined)} combined items to {filename}")
    
    return all_items_combined

def generate_all_categories():
    """Generate all search categories organized by session"""
    
    # Session 1: Cheap Rare items (0-10 chaos)
    session1 = []
    for i in range(0, 10):
        session1.append((f"Rare_{i}-{i+1}c", {
            "filters": {
                "type_filters": {"filters": {"rarity": {"option": "rare"}}},
                "trade_filters": {"filters": {"price": {"option": "chaos", "min": i, "max": i+1}}}
            }
        }))
    
    # Session 2: Mid Rare items (10-50 chaos)
    session2 = []
    ranges = [(10, 12), (12, 15), (15, 18), (18, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 45), (45, 50)]
    for min_p, max_p in ranges:
        session2.append((f"Rare_{min_p}-{max_p}c", {
            "filters": {
                "type_filters": {"filters": {"rarity": {"option": "rare"}}},
                "trade_filters": {"filters": {"price": {"option": "chaos", "min": min_p, "max": max_p}}}
            }
        }))
    
    # Session 3: Expensive Rare items (50+ chaos)
    session3 = []
    ranges = [(50, 60), (60, 70), (70, 80), (80, 90), (90, 100), (100, 120), (120, 150), (150, 200), (200, 300), (300, 500), (500, None)]
    for min_p, max_p in ranges:
        price_desc = f"{min_p}-{max_p or 'inf'}c"
        filters = {
            "filters": {
                "type_filters": {"filters": {"rarity": {"option": "rare"}}},
                "trade_filters": {"filters": {"price": {"option": "chaos", "min": min_p}}}
            }
        }
        if max_p:
            filters["filters"]["trade_filters"]["filters"]["price"]["max"] = max_p
        session3.append((f"Rare_{price_desc}", filters))
    
    # Session 4: All Unique items
    session4 = []
    ranges = [(None, 5), (5, 10), (10, 15), (15, 20), (20, 30), (30, 40), (40, 50), (50, 75), (75, 100), (100, 150), (150, 200), (200, None)]
    for min_p, max_p in ranges:
        price_desc = f"{min_p or 0}-{max_p or 'inf'}c"
        filters = {
            "filters": {
                "type_filters": {"filters": {"rarity": {"option": "unique"}}},
                "trade_filters": {"filters": {"price": {"option": "chaos"}}}
            }
        }
        if min_p:
            filters["filters"]["trade_filters"]["filters"]["price"]["min"] = min_p
        if max_p:
            filters["filters"]["trade_filters"]["filters"]["price"]["max"] = max_p
        session4.append((f"Unique_{price_desc}", filters))
    
    # Session 5: Magic items
    session5 = []
    ranges = [(None, 2), (2, 5), (5, 10), (10, 20), (20, None)]
    for min_p, max_p in ranges:
        price_desc = f"{min_p or 0}-{max_p or 'inf'}c"
        filters = {
            "filters": {
                "type_filters": {"filters": {"rarity": {"option": "magic"}}},
                "trade_filters": {"filters": {"price": {"option": "chaos"}}}
            }
        }
        if min_p:
            filters["filters"]["trade_filters"]["filters"]["price"]["min"] = min_p
        if max_p:
            filters["filters"]["trade_filters"]["filters"]["price"]["max"] = max_p
        session5.append((f"Magic_{price_desc}", filters))
    
    return {
        1: session1,
        2: session2,
        3: session3,
        4: session4,
        5: session5
    }

def scrape_session(session_number, categories):
    """Scrape a single session"""
    create_output_directory()
    
    # Load previous progress
    completed_categories, seen_item_ids = load_progress()
    
    print(f"\n{'='*70}")
    print(f"SESSION {session_number} SCRAPER")
    print(f"{'='*70}")
    print(f"Categories in this session: {len(categories)}")
    print(f"Already completed categories: {len(completed_categories)}")
    print(f"Already collected unique items: {len(seen_item_ids)}")
    print(f"Estimated time: {(len(categories) * DELAY_BETWEEN_SEARCHES) / 60:.1f} minutes")
    print(f"{'='*70}")
    
    all_items_collected = []
    
    start_time = datetime.now()
    
    for cat_num, (category_name, filters) in enumerate(categories, 1):
        # Skip if already completed
        if category_name in completed_categories:
            print(f"\n[{cat_num}/{len(categories)}] ⏭ Skipping {category_name} (already completed)")
            continue
        
        elapsed = (datetime.now() - start_time).total_seconds()
        avg_time = elapsed / cat_num if cat_num > 0 else 0
        remaining = len(categories) - cat_num
        eta = avg_time * remaining
        
        print(f"\n{'='*70}")
        print(f"[{cat_num}/{len(categories)}] Progress: {(cat_num/len(categories)*100):.1f}%")
        print(f"ETA: {eta/60:.1f}min | Total unique items: {len(seen_item_ids):,}")
        print(f"{'='*70}")
        
        # SEARCH → FETCH → SAVE
        items = scrape_category(category_name, filters)
        
        # Track unique items
        new_items = 0
        for item_data in items:
            item_id = item_data.get('id')
            if item_id and item_id not in seen_item_ids:
                all_items_collected.append(item_data)
                seen_item_ids.add(item_id)
                new_items += 1
        
        if new_items > 0:
            print(f"  → Added {new_items} new unique items")
        
        # Mark as completed
        completed_categories.add(category_name)
        
        # Save progress after each category
        save_progress(completed_categories, seen_item_ids)
        
        # Delay before next category
        if cat_num < len(categories):
            time.sleep(DELAY_BETWEEN_SEARCHES)
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"\n{'='*70}")
    print(f"✓ SESSION {session_number} COMPLETE!")
    print(f"{'='*70}")
    print(f"New items this session: {len(all_items_collected):,}")
    print(f"Total unique items: {len(seen_item_ids):,}")
    print(f"Time taken: {duration / 60:.1f} minutes")
    print(f"{'='*70}")

def create_master_file():
    """Combine all individual files into one master file"""
    all_items = []
    seen_ids = set()
    
    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith('.json') and filename != 'progress.json' and not filename.startswith('MASTER'):
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get('items', []):
                    item_id = item.get('id')
                    if item_id and item_id not in seen_ids:
                        all_items.append(item)
                        seen_ids.add(item_id)
    
    master_file = f"{OUTPUT_DIR}/MASTER_{len(all_items)}_items.json"
    with open(master_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'total_unique_items': len(all_items),
                'scrape_date': datetime.now().isoformat()
            },
            'items': all_items
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Master file created: {master_file}")
    print(f"  Total unique items: {len(all_items):,}")

if __name__ == "__main__":
    print("="*70)
    print("PoE2 SESSION-BASED SCRAPER")
    print("="*70)
    
    sessions = generate_all_categories()
    
    print("\nAvailable sessions:")
    print("  1. Cheap Rare (0-10c)      - 10 searches")
    print("  2. Mid Rare (10-50c)       - 10 searches")
    print("  3. Expensive Rare (50c+)   - 11 searches")
    print("  4. All Unique items        - 12 searches")
    print("  5. All Magic items         - 5 searches")
    print("  6. Create master file (combine all)")
    print("  0. Exit")
    
    while True:
        choice = input("\nWhich session to run? (0-6): ").strip()
        
        if choice == "0":
            print("Exiting...")
            break
        elif choice == "6":
            create_master_file()
            break
        elif choice in ["1", "2", "3", "4", "5"]:
            session_num = int(choice)
            scrape_session(session_num, sessions[session_num])
            
            again = input("\nRun another session? (yes/no): ").strip().lower()
            if again != 'yes':
                print("\nDon't forget to run option 6 to create the master file!")
                break
        else:
            print("Invalid choice!")