import csv
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

with open('ingredients.csv', 'r') as file:
    reader = csv.reader(file)
    next = csv.reader(file)
    for row in reader:
        cursor.execute('INSERT INTO recipes_ingredient (name, measurement_unit) VALUES (?, ?)', (row[0], row[1]))
conn.commit()
conn.close()
