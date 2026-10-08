import pandas as pd
import json
from DbConnector import DbConnector
from math import radians, sin, cos, sqrt, atan2

NROWS: int = None

class InsertData:

    def __init__(self):
        self.connection = DbConnector()
        self.db_connection = self.connection.db_connection
        self.cursor = self.connection.cursor

    def haversine(self, lon1, lat1, lon2, lat2):
        R = 6371.0

        dlon = radians(lon2 - lon1)
        dlat = radians(lat2 - lat1)

        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1))
            * cos(radians(lat2))
            * sin(dlon / 2) ** 2
        )

        return 2 * R * atan2(sqrt(a), sqrt(1 - a))

    def insert_trips(self) -> None:
        
        # Les data
        df = pd.read_csv("data/porto.csv", nrows=NROWS)

        # Cleaning fra EDA
        df = df[df["MISSING_DATA"] == False].copy()
        df = df.drop(columns=["MISSING_DATA"])
        df = df.drop_duplicates().copy()

        # Konverter til datetime
        df["start_time"] = pd.to_datetime(df["TIMESTAMP"], unit="s")

        trip_query = """
        INSERT INTO Trip (
            trip_id,
            call_type,
            origin_call,
            origin_stand,
            taxi_id,
            start_time,
            n_points,
            duration_s,
            distance_km
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        gps_query = """
        INSERT INTO GPSPoint (
            trip_fk,
            point_no,
            longitude,
            latitude
        )
        VALUES (%s, %s, %s, %s)
        """

        gps_batch = []
        batch_size = 10000

        for _, row in df.iterrows():

            polyline = json.loads(row["POLYLINE"])
            
            n_points = len(polyline)
            duration_s = max(0, (n_points - 1) * 15)
    
            distance_km = 0.0
    
            for i in range(1, n_points):
                lon1, lat1 = polyline[i - 1]
                lon2, lat2 = polyline[i]
    
                distance_km += self.haversine(lon1, lat1, lon2, lat2)

            values = (
                int(row["TRIP_ID"]),
                row["CALL_TYPE"],
                None if pd.isna(row["ORIGIN_CALL"]) else int(row["ORIGIN_CALL"]),
                None if pd.isna(row["ORIGIN_STAND"]) else int(row["ORIGIN_STAND"]),
                int(row["TAXI_ID"]),
                row["start_time"].to_pydatetime(),
                n_points,
                duration_s,
                distance_km
            )

            self.cursor.execute(trip_query, values)

            trip_fk = self.cursor.lastrowid

            for point_no, point in enumerate(polyline):

                gps_batch.append((
                    trip_fk,
                    point_no,
                    point[0],
                    point[1]
                ))

                if len(gps_batch) >= batch_size:
                    self.cursor.executemany(gps_query, gps_batch)
                    gps_batch.clear()

        if gps_batch:
            self.cursor.executemany(gps_query, gps_batch)

        self.db_connection.commit()

def main():
    program = None

    try:
        program = InsertData()
        program.insert_trips()

    except Exception as e:
        print("ERROR:", e)

    finally:
        if program:
            program.connection.close_connection()


if __name__ == "__main__":
    main()