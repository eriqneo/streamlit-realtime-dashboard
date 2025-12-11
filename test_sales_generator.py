import random
import time
import math

# Define dynamic product catalog
CATEGORIES = {
    "Electronics": {"price_range": (80, 400), "weight": 0.30},
    "Apparel": {"price_range": (25, 120), "weight": 0.35},
    "Home & Garden": {"price_range": (40, 200), "weight": 0.20},
    "Beauty": {"price_range": (15, 90), "weight": 0.10},
    "Toys & Games": {"price_range": (20, 150), "weight": 0.05},
}

def generate_sales_event(base_hourly_revenue=30000):
    """
    Simulates a realistic e-commerce transaction.
    - base_hourly_revenue: target revenue per hour (e.g., 30000 = $30K/hr)
    """
    t = time.time()
    
    # Simulate time-of-day effect: peak at 2 PM (14:00)
    hour = (int(t) // 3600) % 24
    peak_factor = 1.0 + 0.3 * math.sin((hour - 14) * math.pi / 12)  # +30% at peak
    
    # Base traffic: scale to hit target revenue (~$100 AOV assumption)
    base_events_per_sec = base_hourly_revenue / 3600 / 100
    
    # Adjust for peak
    events_per_sec = base_events_per_sec * peak_factor
    
    # Decide how many orders this tick (1 to 4)
    num_orders = random.choices([1, 2, 3, 4], weights=[0.6, 0.25, 0.1, 0.05])[0]
    
    events = []
    for _ in range(num_orders):
        # Choose category by weight
        categories, weights = zip(*[(k, v["weight"]) for k, v in CATEGORIES.items()])
        category = random.choices(categories, weights=weights)[0]
        min_p, max_p = CATEGORIES[category]["price_range"]
        price = round(random.uniform(min_p, max_p), 2)
        
        # Simulate concurrent traffic (for conversion rate later)
        traffic = max(50, int(events_per_sec * 3600 * random.uniform(0.8, 1.2)))
        
        events.append({
            "timestamp": t,
            "order_id": f"ord_{random.randint(10000, 99999)}",
            "product_category": category,
            "price": price,
            "traffic_this_min": traffic
        })
    
    return events


# ----------------------------
# Test the generator
# ----------------------------
if __name__ == "__main__":
    print("🚀 Simulating live sales events (mid-size e-commerce: ~$30K/hour)...\n")
    print("Press Ctrl+C to stop.\n")
    
    try:
        for i in range(10):  # Test 10 batches
            events = generate_sales_event(base_hourly_revenue=30000)
            total_batch_revenue = sum(e["price"] for e in events)
            print(f"🕒 Batch {i+1:2d} | {len(events)} order(s) | Revenue: ${total_batch_revenue:.2f}")
            for e in events:
                print(f"   → {e['product_category']:<15} | ${e['price']:<8.2f} | Traffic: {e['traffic_this_min']}/min")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user.")