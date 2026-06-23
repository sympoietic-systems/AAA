#!/usr/bin/env python3
"""
porter.py - Port research tasks between local and remote setups.

Usage:
  # Export a research task from local database to a JSON bundle
  python scripts/porter.py --export <task_id> --out <output_json> [--db <path_to_db>]

  # Import a research task from a JSON bundle into the database
  python scripts/porter.py --import <path_to_json> [--db <path_to_db>]
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime

# Tables related to a research task
TABLES = [
    "research_tasks",
    "research_branches",
    "scraped_assets",
    "research_plans",
    "research_steps",
    "research_step_results",
    "research_meta_log"
]

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        value = row[idx]
        # Serialize bytes to hex string for JSON compatibility
        if isinstance(value, bytes):
            value = {"__bytes_hex__": value.hex()}
        d[col[0]] = value
    return d

def decode_bytes(value):
    if isinstance(value, dict) and "__bytes_hex__" in value:
        return bytes.fromhex(value["__bytes_hex__"])
    return value

def get_db_connection(db_path):
    if not os.path.exists(db_path):
        print(f"Warning: Database path '{db_path}' does not exist. A new database will be created.", file=sys.stderr)
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    return conn

def export_task(task_id, db_path, out_path):
    print(f"Connecting to database: {db_path}")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Fetch the main research task
    cursor.execute("SELECT * FROM research_tasks WHERE id = ?", (task_id,))
    task_row = cursor.fetchone()
    if not task_row:
        print(f"Error: Research task '{task_id}' not found in the database.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conversation_id = task_row.get("conversation_id")
    print(f"Exporting task '{task_id}' (conversation: {conversation_id})...")

    bundle = {
        "export_timestamp": datetime.utcnow().isoformat(),
        "task_id": task_id,
        "conversation_id": conversation_id,
        "data": {}
    }

    # 2. Fetch related rows from all research tables
    for table in TABLES:
        # Most research tables have a direct `task_id` column
        query = f"SELECT * FROM {table} WHERE task_id = ?"
        cursor.execute(query, (task_id,))
        rows = cursor.fetchall()
        bundle["data"][table] = rows
        print(f"  - Table {table:25s}: {len(rows)} row(s)")

    # 3. Read synthesis file from disk if it exists
    synthesis_filename = f"research-synthesis-{task_id}.md"
    # Find in data/conversations/{conversation_id}/{synthesis_filename}
    synthesis_path = os.path.join("data", "conversations", conversation_id, synthesis_filename)
    if os.path.exists(synthesis_path):
        print(f"  - Found synthesis file on disk: {synthesis_path}")
        with open(synthesis_path, "r", encoding="utf-8") as f:
            bundle["synthesis_file"] = {
                "filename": synthesis_filename,
                "content": f.read()
            }
    else:
        print(f"  - No synthesis file found on disk at: {synthesis_path}")
        bundle["synthesis_file"] = None

    # Write out the JSON bundle
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)

    print(f"\nSuccessfully exported task to: {out_path}")
    conn.close()

def import_task(json_path, db_path):
    print(f"Loading bundle from: {json_path}")
    if not os.path.exists(json_path):
        print(f"Error: JSON file '{json_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    task_id = bundle.get("task_id")
    conversation_id = bundle.get("conversation_id")
    print(f"Importing task '{task_id}' (conversation: {conversation_id})...")

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Lazily provision the shell conversation to satisfy foreign key constraints
    cursor.execute(
        "INSERT OR IGNORE INTO conversations (id, title, agent_id) VALUES (?, ?, ?)",
        (conversation_id, "Imported Research Space", "system")
    )
    print(f"  - Ensured conversation '{conversation_id}' exists in target database.")

    # 2. Insert rows into research tables
    for table, rows in bundle["data"].items():
        if not rows:
            continue

        # Get column names from the first row
        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        
        insert_query = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
        
        # Prepare parameters list and handle bytes conversions
        param_list = []
        for row in rows:
            params = [decode_bytes(row[col]) for col in columns]
            param_list.append(params)

        cursor.executemany(insert_query, param_list)
        print(f"  - Imported {len(rows)} row(s) into table: {table}")

    conn.commit()
    conn.close()
    print("  - Database records written successfully.")

    # 3. Write synthesis file back to disk if present in bundle
    synth_file = bundle.get("synthesis_file")
    if synth_file:
        dest_dir = os.path.join("data", "conversations", conversation_id)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, synth_file["filename"])
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(synth_file["content"])
        print(f"  - Synthesis report written to disk: {dest_path}")

    print(f"\nSuccessfully imported task '{task_id}' into database.")

def main():
    parser = argparse.ArgumentParser(description="Port research tasks between environments.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", help="Task ID to export")
    group.add_argument("--import-file", dest="import_file", help="Path to JSON bundle to import")
    
    parser.add_argument("--out", help="Output file path (required for --export)")
    parser.add_argument("--db", default="data/aaa.db", help="Path to SQLite database (default: data/aaa.db)")

    args = parser.parse_args()

    if args.export:
        if not args.out:
            parser.error("--out is required when using --export")
        export_task(args.export, args.db, args.out)
    elif args.import_file:
        import_task(args.import_file, args.db)

if __name__ == "__main__":
    main()
