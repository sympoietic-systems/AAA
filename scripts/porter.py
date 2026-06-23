#!/usr/bin/env python3
"""
porter.py - Port research tasks between local and remote setups.

Usage:
  # Export all research tasks to a JSON bundle
  python scripts/porter.py --export all --out <output_json> [--db <path_to_db>]

  # Export a specific research task from local database to a JSON bundle
  python scripts/porter.py --export <task_id> --out <output_json> [--db <path_to_db>]

  # Import research tasks from a JSON bundle into the database (supports bulk and single task bundles)
  python scripts/porter.py --import-file <path_to_json> [--db <path_to_db>]
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
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    if not os.path.exists(db_path):
        print(f"Warning: Database path '{db_path}' does not exist. A new database will be created.", file=sys.stderr)
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    return conn

def get_proj_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_synthesis_file_path(proj_root, conversation_id, task_id):
    # Matches backend UPLOAD_DIR = os.path.join("backend", "data", "uploads")
    return os.path.abspath(
        os.path.join(
            proj_root,
            "backend",
            "data",
            "uploads",
            conversation_id,
            f"research-synthesis-{task_id}.md"
        )
    )

def export_all_tasks(db_path, out_path, proj_root):
    print(f"Connecting to database: {db_path}")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM research_tasks")
        task_ids = [row["id"] for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        print(f"Error: Could not query research_tasks table. Schema might not be initialized. Details: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not task_ids:
        print("No research tasks found in the database.", file=sys.stderr)
        conn.close()
        sys.exit(0)

    print(f"Found {len(task_ids)} research task(s) to export.")

    bundle = {
        "export_timestamp": datetime.utcnow().isoformat(),
        "is_bulk": True,
        "tasks": []
    }

    for task_id in task_ids:
        # Fetch the main research task
        cursor.execute("SELECT * FROM research_tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
        conversation_id = task_row.get("conversation_id")

        task_bundle = {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "data": {}
        }

        # Fetch related rows from all research tables
        for table in TABLES:
            col_name = "id" if table == "research_tasks" else "task_id"
            query = f"SELECT * FROM {table} WHERE {col_name} = ?"
            cursor.execute(query, (task_id,))
            rows = cursor.fetchall()
            task_bundle["data"][table] = rows

        # Read synthesis file from disk if it exists
        if conversation_id:
            synthesis_filename = f"research-synthesis-{task_id}.md"
            synthesis_path = get_synthesis_file_path(proj_root, conversation_id, task_id)
            if os.path.exists(synthesis_path):
                with open(synthesis_path, "r", encoding="utf-8") as f:
                    task_bundle["synthesis_file"] = {
                        "filename": synthesis_filename,
                        "content": f.read()
                    }
            else:
                task_bundle["synthesis_file"] = None
        else:
            task_bundle["synthesis_file"] = None

        bundle["tasks"].append(task_bundle)
        print(f"  - Packed task '{task_id}' (conversation: {conversation_id})")

    # Write out the JSON bundle
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)

    print(f"\nSuccessfully exported {len(task_ids)} task(s) to: {out_path}")
    conn.close()

def export_task(task_id, db_path, out_path, proj_root):
    if task_id.lower() == "all":
        export_all_tasks(db_path, out_path, proj_root)
        return

    print(f"Connecting to database: {db_path}")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Fetch the main research task
    try:
        cursor.execute("SELECT * FROM research_tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
    except sqlite3.OperationalError as e:
        print(f"Error: Could not query research_tasks table. Schema might not be initialized. Details: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

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
        col_name = "id" if table == "research_tasks" else "task_id"
        query = f"SELECT * FROM {table} WHERE {col_name} = ?"
        cursor.execute(query, (task_id,))
        rows = cursor.fetchall()
        bundle["data"][table] = rows
        print(f"  - Table {table:25s}: {len(rows)} row(s)")

    # 3. Read synthesis file from disk if it exists
    if conversation_id:
        synthesis_filename = f"research-synthesis-{task_id}.md"
        synthesis_path = get_synthesis_file_path(proj_root, conversation_id, task_id)
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
    else:
        print(f"  - No conversation associated with this task; skipping synthesis file check.")
        bundle["synthesis_file"] = None

    # Write out the JSON bundle
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)

    print(f"\nSuccessfully exported task to: {out_path}")
    conn.close()

def import_task(json_path, db_path, proj_root):
    print(f"Loading bundle from: {json_path}")
    if not os.path.exists(json_path):
        print(f"Error: JSON file '{json_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    print(f"Connecting to database: {db_path}")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Determine if it's a single task or bulk export
    tasks_to_import = []
    if bundle.get("is_bulk"):
        tasks_to_import = bundle.get("tasks", [])
        print(f"Bulk bundle loaded. Importing {len(tasks_to_import)} task(s)...")
    else:
        tasks_to_import = [bundle]
        print(f"Single task bundle loaded.")

    for idx, t_bundle in enumerate(tasks_to_import):
        task_id = t_bundle.get("task_id")
        conversation_id = t_bundle.get("conversation_id")
        print(f"\n[{idx+1}/{len(tasks_to_import)}] Importing task '{task_id}' (conversation: {conversation_id})...")

        # 1. Lazily provision the shell conversation to satisfy foreign key constraints
        if conversation_id:
            cursor.execute(
                "INSERT OR IGNORE INTO conversations (id, title, agent_id) VALUES (?, ?, ?)",
                (conversation_id, "Imported Research Space", "system")
            )
            print(f"  - Ensured conversation '{conversation_id}' exists in target database.")
        else:
            print("  - No associated conversation for this task; skipping conversation provisioning.")

        # 2. Insert rows into research tables
        for table, rows in t_bundle["data"].items():
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

        # 3. Write synthesis file back to disk if present in bundle
        synth_file = t_bundle.get("synthesis_file")
        if synth_file and conversation_id:
            dest_path = get_synthesis_file_path(proj_root, conversation_id, task_id)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(synth_file["content"])
            print(f"  - Synthesis report written to disk: {dest_path}")

    conn.commit()
    conn.close()
    print("\nAll database records written successfully.")

def main():
    parser = argparse.ArgumentParser(description="Port research tasks between environments.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", help="Task ID to export, or 'all' to export all tasks")
    group.add_argument("--import-file", dest="import_file", help="Path to JSON bundle to import")
    
    parser.add_argument("--out", help="Output file path (required for --export)")
    parser.add_argument("--db", default="data/aaa.db", help="Path to SQLite database (default: data/aaa.db)")

    args = parser.parse_args()

    proj_root = get_proj_root()
    
    # Replicate native get_db_path path resolution
    resolved_db_path = args.db
    if not os.path.isabs(args.db):
        resolved_db_path = os.path.abspath(os.path.join(proj_root, "backend", args.db))

    if args.export:
        if not args.out:
            parser.error("--out is required when using --export")
        export_task(args.export, resolved_db_path, args.out, proj_root)
    elif args.import_file:
        import_task(args.import_file, resolved_db_path, proj_root)

if __name__ == "__main__":
    main()
