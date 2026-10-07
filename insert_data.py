import pandas as pd
import json
from DbConnector import DbConnector

NROWS: int = 100_000

class InsertData:

    def __init__(self):
        self.connection = DbConnector()
        self.db_connection = self.connection.db_connection
        self.cursor = self.connection.cursor

    def insert_trips(self) -> None:
        
        # Les data
        df = pd.read_csv("data/porto.csv", nrows=NROWS)

        # Cleaning fra EDA
        df = df[df["MISSING_DATA"] == False].copy()
        df = df.drop(columns=["MISSING_DATA"])
        df = df.drop_duplicates().copy()

        # Konverter til datetime
        df["start_time"] = pd.to_datetime(df["TIMESTAMP"], unit="s")

        df["n_points"] = df["POLYLINE"].apply(lambda x: len(json.loads(x)))

        query: str = """
        INSERT INTO Trip (
            trip_id,
            call_type,
            origin_call,
            origin_stand,
            taxi_id,
            start_time,
            day_type,
            n_points
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        for _, row in df.iterrows():

            values = (
                int(row["TRIP_ID"]),
                row["CALL_TYPE"],
                None if pd.isna(row["ORIGIN_CALL"]) else int(row["ORIGIN_CALL"]),
                None if pd.isna(row["ORIGIN_STAND"]) else int(row["ORIGIN_STAND"]),
                int(row["TAXI_ID"]),
                row["start_time"].to_pydatetime(),
                row["DAY_TYPE"],
                int(row["n_points"])
            )

            self.cursor.execute(query, values)

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