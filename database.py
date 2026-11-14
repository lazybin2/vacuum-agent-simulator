import sqlite3
import pandas as pd


def init_db():
  conn = sqlite3.connect("simulation_logs.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            algorithm TEXT,
            grid_size INT,
            total_steps INT,
            cleaned_spots INT,
            efficiency REAL
        )
    """)
  conn.commit()
  conn.close()


def log_to_db(algorithm, grid_size, total_steps, cleaned_spots, efficiency):
  conn = sqlite3.connect("simulation_logs.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO history (timestamp, algorithm, grid_size, total_steps, cleaned_spots, efficiency)
        VALUES (datetime('now', 'localtime'), ?, ?, ?, ?, ?)
    """,
      (algorithm, grid_size, total_steps, cleaned_spots, efficiency),
  )
  conn.commit()
  conn.close()


def get_db_history():
  conn = sqlite3.connect("simulation_logs.db")
  df = pd.read_sql_query(
      "SELECT * FROM history ORDER BY efficiency DESC, total_steps ASC", conn
  )
  conn.close()
  return df