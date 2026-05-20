import sys, os

sys.path.insert(0, "D:/AAA")

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import MessageRepository, ErrorLogRepository
import numpy as np

db_path = str(get_db_path("data/aaa_test.db"))
conn = init_db(db_path)

cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r["name"] for r in cursor.fetchall()]
print("Tables:", tables)

emb = np.zeros(384, dtype="float32").tobytes()
repo = MessageRepository(db_path)
msg = repo.insert("human", "Hello, world!", emb, "all-MiniLM-L6-v2", 384)
print(f"Inserted: id={msg.id}, speaker={msg.speaker}, content={msg.content}")

msgs = repo.get_recent(10)
print(f"Recent messages: {len(msgs)}")

err_repo = ErrorLogRepository(db_path)
err = err_repo.log_error("test", ValueError("test error"), {"input": "test"})
print(f"Error logged: id={err.id}, module={err.module}, type={err.error_type}")

errors = err_repo.get_recent(5)
print(f"Recent errors: {len(errors)}")

conn.close()
os.remove(db_path)
print("All tests passed!")
