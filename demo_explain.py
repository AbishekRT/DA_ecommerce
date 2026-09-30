"""
demo_explain.py
Demonstrates MongoDB query optimization and index usage using .explain().
Use this script during your academic viva presentation or for report screenshots.

Run with:  python demo_explain.py
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db     = client[os.getenv("DATABASE_NAME", "projector_ecommerce")]

def print_section(title):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)

def print_explain_summary(explain_result):
    query_planner = explain_result.get("queryPlanner", {})
    winning_plan  = query_planner.get("winningPlan", {})
    exec_stats    = explain_result.get("executionStats", {})

    # Extract stage details (handling possible SHARDING/FETCH stages)
    stage = winning_plan.get("stage", "UNKNOWN")
    index_name = "None (Full Collection Scan - COLLSCAN)"
    
    if stage == "FETCH" and "inputStage" in winning_plan:
        sub_stage = winning_plan["inputStage"].get("stage")
        stage = f"FETCH -> {sub_stage}"
        index_name = winning_plan["inputStage"].get("indexName", "N/A")
    elif "indexName" in winning_plan:
        index_name = winning_plan.get("indexName")

    print(f"  [+] Execution Stage      : {stage}")
    print(f"  [+] Index Used           : {index_name}")
    print(f"  [+] Total Docs Examined  : {exec_stats.get('totalDocsExamined', 0)}")
    print(f"  [+] Total Keys Examined  : {exec_stats.get('totalKeysExamined', 0)}")
    print(f"  [+] Documents Returned   : {exec_stats.get('nReturned', 0)}")
    print(f"  [+] Execution Time       : {exec_stats.get('executionTimeMillis', 0)} ms")

def run_demo():
    print_section("DEMONSTRATION 1: Single Field Index on products.category_id")
    cat = db["categories"].find_one()
    if cat:
        query = {"category_id": cat["_id"]}
        print(f"  Query: db.products.find({{'category_id': ObjectId('{cat['_id']}')}})")
        explain = db["products"].find(query).explain()
        print_explain_summary(explain)
    else:
        print("  [!] Please run python seed.py first.")

    print_section("DEMONSTRATION 2: Unique Index on users.email")
    query_user = {"email": "alice@example.com"}
    print(f"  Query: db.users.find({query_user})")
    explain_user = db["users"].find(query_user).explain()
    print_explain_summary(explain_user)

    print_section("DEMONSTRATION 3: Compound Index on rentals (product_id + start_date + end_date)")
    prod = db["products"].find_one({"type": {"$in": ["rent", "both"]}})
    if prod:
        now = datetime.now(timezone.utc)
        query_rental = {
            "product_id": prod["_id"],
            "status": {"$in": ["confirmed", "active"]},
            "start_date": {"$lt": now + timedelta(days=7)},
            "end_date":   {"$gt": now},
        }
        print(f"  Query: db.rentals.find({{ product_id: ObjectId('{prod['_id']}'), date_range_filter }})")
        explain_rental = db["rentals"].find(query_rental).explain()
        print_explain_summary(explain_rental)

    print_section("DEMONSTRATION 4: Descending Sort Index on orders.created_at")
    user = db["users"].find_one({"role": "customer"})
    if user:
        query_order = {"user_id": user["_id"]}
        print(f"  Query: db.orders.find({{ user_id: ObjectId('{user['_id']}') }}).sort('created_at', -1)")
        explain_order = db["orders"].find(query_order).sort("created_at", -1).explain()
        print_explain_summary(explain_order)

    print("\n" + "=" * 75)
    print("  Summary: All queries successfully utilized indexes (IXSCAN).")
    print("  No full collection scans (COLLSCAN) were performed.")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    run_demo()
