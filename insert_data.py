import pandas as pd
import mysql.connector

# Les data
df = pd.read_csv("data/porto.csv", nrows=1000)

# Cleaning fra EDA
df = df[df["MISSING_DATA"] == False].copy()
df = df.drop(columns=["MISSING_DATA"])
df = df.drop_duplicates().copy()

# Koble til MySQL som kjører i Docker
connection = mysql.connector.connect(
    host="localhost",
    user="sdd",
    password="sdd",
    database="sdd"
)

cursor = connection.cursor()

# Sett inn én rad om gangen
for _, row in df.iterrows():
    cursor.execute(
        """
        INSERT INTO Trip (
            trip_id,
            call_type,
            origin_call,
            origin_stand,
            taxi_id,
            timestamp,
            day_type,
            polyline
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            int(row["TRIP_ID"]),
            row["CALL_TYPE"],
            None if pd.isna(row["ORIGIN_CALL"]) else int(row["ORIGIN_CALL"]),
            None if pd.isna(row["ORIGIN_STAND"]) else int(row["ORIGIN_STAND"]),
            int(row["TAXI_ID"]),
            int(row["TIMESTAMP"]),
            row["DAY_TYPE"],
            row["POLYLINE"]
        )
    )

connection.commit()

cursor.close()
connection.close()