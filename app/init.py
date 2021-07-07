import sqlite3
import uuid
from app import DATABASE

db = sqlite3.connect(DATABASE)

with open('schema.sql', 'r') as f:
    db.cursor().executescript(f.read())
    db.commit()

with open('secret', 'wb') as f:
    f.write(uuid.uuid4().bytes)