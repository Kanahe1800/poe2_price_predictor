import requests
import json
import time

"""
PoE2 Trade API Basic Scraper
This script demonstrates how to query the Path of Exile 2 trade API
"""

# API endpoints
SEARCH_API = "https://www.pathofexile.com/api/trade2/search/poe2/Standard"
FETCH_API = "https://www.pathofexile.com/api/trade2/fetch/"

def search_items(query_params):
    """
    Search for items based on query parameters
    Returns list of item IDs
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.post(SEARCH_API, json=query_params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data.get('total', 0)} items")
        return data.get('result', []), data.get('id', '')
    else:
        print(f"Error: {response.status_code}")
        return [], ''

def fetch_item_details(item_ids, query_id):
    """
    Fetch detailed information for specific items
    item_ids: list of item IDs (max 10 at a time)
    query_id: the search query ID from search results
    """
    # API allows fetching up to 10 items at once
    item_ids_str = ','.join(item_ids[:10])
    
    url = f"{FETCH_API}{item_ids_str}?query={query_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching items: {response.status_code}")
        return None
    
def print_item_readable(item_data):
    """
    Print a single item in a readable format
    """
    try:
        item = item_data.get('item', {})
        listing = item_data.get('listing', {})
        
        # Header
        print("\n" + "="*70)
        
        # Item name and type
        name = item.get('name', '')
        type_line = item.get('typeLine', '')
        base_type = item.get('baseType', '')
        
        if name:
            print(f"📦 {name}")
            print(f"   {type_line}")
        else:
            print(f"📦 {type_line}")
        
        # Rarity
        frame_type = item.get('frameType', 0)
        rarity_map = {0: '⚪ Normal', 1: '🔵 Magic', 2: '🟡 Rare', 3: '🟠 Unique'}
        print(f"   {rarity_map.get(frame_type, 'Unknown')}")
        
        # Item Level
        ilvl = item.get('ilvl', 'N/A')
        print(f"   Item Level: {ilvl}")
        
        # Price
        price_info = listing.get('price', {})
        if price_info:
            amount = price_info.get('amount', 0)
            currency = price_info.get('currency', 'unknown')
            print(f"\n💰 Price: {amount} {currency}")
        
        # Implicit Mods
        implicit_mods = item.get('implicitMods', [])
        if implicit_mods:
            print(f"\n✨ Implicit Modifiers:")
            for mod in implicit_mods:
                print(f"   • {mod}")
        
        # Explicit Mods
        explicit_mods = item.get('explicitMods', [])
        if explicit_mods:
            print(f"\n⭐ Explicit Modifiers:")
            for mod in explicit_mods:
                print(f"   • {mod}")
        
        # Crafted Mods
        crafted_mods = item.get('craftedMods', [])
        if crafted_mods:
            print(f"\n🔨 Crafted Modifiers:")
            for mod in crafted_mods:
                print(f"   • {mod}")
        
        # Enchant Mods
        enchant_mods = item.get('enchantMods', [])
        if enchant_mods:
            print(f"\n🌟 Enchantments:")
            for mod in enchant_mods:
                print(f"   • {mod}")
        
        # Fractured Mods
        fractured_mods = item.get('fracturedMods', [])
        if fractured_mods:
            print(f"\n💎 Fractured Modifiers:")
            for mod in fractured_mods:
                print(f"   • {mod}")
        
        # Properties (like weapon damage, armour, etc.)
        properties = item.get('properties', [])
        if properties:
            print(f"\n📊 Properties:")
            for prop in properties:
                prop_name = prop.get('name', '')
                values = prop.get('values', [])
                if values:
                    value_str = ', '.join([str(v[0]) for v in values])
                    print(f"   • {prop_name}: {value_str}")
                else:
                    print(f"   • {prop_name}")
        
        # Requirements
        requirements = item.get('requirements', [])
        if requirements:
            print(f"\n📋 Requirements:")
            for req in requirements:
                req_name = req.get('name', '')
                values = req.get('values', [])
                if values:
                    value_str = ', '.join([str(v[0]) for v in values])
                    print(f"   • {req_name}: {value_str}")
        
        # Sockets
        sockets = item.get('sockets', [])
        if sockets:
            socket_groups = {}
            for socket in sockets:
                group = socket.get('group', 0)
                colour = socket.get('sColour', 'X')
                if group not in socket_groups:
                    socket_groups[group] = []
                socket_groups[group].append(colour)
            
            print(f"\n🔌 Sockets:")
            for group, colours in sorted(socket_groups.items()):
                print(f"   • {'-'.join(colours)}")
         
        print("="*70)
        
    except Exception as e:
        print(f"Error printing item: {e}")

def print_items_summary(items_data):
    """
    Print a summary of all items
    """
    results = items_data.get('result', [])
    
    if not results:
        print("No items found!")
        return
    
    print(f"\n{'='*70}")
    print(f"Found {len(results)} items")
    print(f"{'='*70}")
    
    for i, item_data in enumerate(results, 1):
        print(f"\n[Item {i}/{len(results)}]")
        print_item_readable(item_data)

    
# Example 2: Simple search for any listed items
def simple_search():
    """
    Simple search for any items (to explore data structure)
    """
    query = {
        "query": {
            "status": {
                "option": "online"
            }
        },
        "sort": {
            "price": "asc"
        }
    }
    
    print("Searching for any items...")
    item_ids, query_id = search_items(query)
    
    if item_ids:
        print(f"\nFetching details for first 10 items...")
        time.sleep(1)
    
        
    item_details = fetch_item_details(item_ids, query_id)
    print_items_summary(item_details)
        
    #     if item_details:
    #         with open('poe2_sample.json', 'w', encoding='utf-8') as f:
    #             json.dump(item_details, f, indent=2, ensure_ascii=False)
            
    #         print(f"\nSaved items to poe2_sample.json")
    
    # return item_details



simple_search()