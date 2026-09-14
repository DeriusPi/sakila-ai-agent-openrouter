import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="0913348843a",
    database="sakila"
)

print("Kết nối MySQL thành công!")

cursor = conn.cursor()

cursor.execute("SHOW TABLES")

for table in cursor:
    print(table)

cursor.close()
conn.close()
