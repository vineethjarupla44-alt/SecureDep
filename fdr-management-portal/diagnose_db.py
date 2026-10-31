import os
import socket
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

host = os.getenv("DB_HOST", "localhost")
port = int(os.getenv("DB_PORT", 3306))
user = os.getenv("DB_USER", "root")
password = os.getenv("DB_PASSWORD", "")
dbname = os.getenv("DB_NAME", "fdr_management")

print(f"=== DATABASE DIAGNOSTIC ===")
print(f"Target: {host}:{port}, Database: {dbname}, User: {user}")

# 1. Socket check
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3.0)
try:
    target_ip = "127.0.0.1" if host in ("localhost", "127.0.0.1") else host
    result = s.connect_ex((target_ip, port))
    if result == 0:
        print(f"[OK] Port {port} is OPEN and accepting connections on {target_ip}.")
        port_open = True
    else:
        print(f"[FAIL] Port {port} is CLOSED or refused on {target_ip} (Error code: {result}).")
        port_open = False
except Exception as e:
    print(f"[ERROR] Socket error connecting to {host}:{port}: {e}")
    port_open = False
finally:
    s.close()

# 2. PyMySQL direct connection check
if port_open:
    import pymysql
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname,
            connect_timeout=5,
        )
        print(f"[OK] Successfully authenticated and connected to database '{dbname}'!")
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES;")
            tables = [r[0] for r in cur.fetchall()]
            print(f"[OK] Existing tables in '{dbname}': {len(tables)} tables found ({', '.join(tables[:5])}...)")
        conn.close()
    except pymysql.MySQLError as err:
        print(f"[ERROR] MySQL authentication/connection error: {err}")
else:
    print("[INFO] MySQL Server daemon is not actively listening on port 3306.")
