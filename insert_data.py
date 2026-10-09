import pandas as pd
import json
from DbConnector import DbConnector
from math import radians, sin, cos, sqrt, atan2, isfinite

NROWS = None

# Et steg på mer enn 1 km mellom to punkter (15 s) tilsvarer over 240 km/t,
# og regnes som et GPS-hopp. Slike steg tas ikke med i distance_km.
MAX_STEP_KM = 1.0


def parse_polyline(value):
    """Valider hele GPS-listen uten å fjerne punkter eller endre rekkefølgen."""
    if not isinstance(value, str):
        raise ValueError("POLYLINE mangler eller er ikke tekst")
    points = json.loads(value)
    if not isinstance(points, list):
        raise ValueError("POLYLINE må være en liste")

    for index, point in enumerate(points):
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"Punkt {index} må inneholde [lon, lat]")
        lon, lat = point
        if any(
            isinstance(x, bool)
            or not isinstance(x, (int, float))
            or not isfinite(x)
            for x in (lon, lat)
        ):
            raise ValueError(f"Punkt {index} har ugyldige koordinattall")
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(f"Punkt {index} er utenfor koordinatgrensene")

    # Tomme lister og 1–2 punkter beholdes for oppgave 7.
    return points


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
        # Ikke importer på nytt over en fullført eller delvis import.
        for table in ("Trip", "GPSPoint"):
            self.cursor.execute(f"SELECT EXISTS(SELECT 1 FROM {table})")
            if self.cursor.fetchone()[0]:
                raise RuntimeError(
                    "Databasen inneholder allerede data. "
                    "Import krever tomme tabeller. Kjør schema.sql bare hvis "
                    "du ønsker å slette eksisterende data og importere på nytt."
                )

        # Les data
        df = pd.read_csv("data/porto.csv", nrows=NROWS)

        # Cleaning fra EDA
        df = df[df["MISSING_DATA"] == False].copy()
        df = df.drop(columns=["MISSING_DATA"])

        # Fjern bare helt identiske rader. Ulike rader med samme TRIP_ID
        # beholdes og får hver sin unike id fra databasen.
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
        trips_inserted = 0
        rejected_rows = []

        for source_index, row in df.iterrows():

            try:
                polyline = parse_polyline(row["POLYLINE"])
            except ValueError as error:
                # Original radposisjon beholdes gjennom filtrering/duplikatfjerning.
                rejected_rows.append((source_index + 2, row["TRIP_ID"], str(error)))
                continue
            
            n_points = len(polyline)
            duration_s = max(0, (n_points - 1) * 15)
    
            distance_km = 0.0
    
            for i in range(1, n_points):
                lon1, lat1 = polyline[i - 1]
                lon2, lat2 = polyline[i]
    
                step_km = self.haversine(lon1, lat1, lon2, lat2)
                if step_km <= MAX_STEP_KM:
                    distance_km += step_km

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

            # Commit underveis, så ikke alt går tapt hvis noe stopper
            trips_inserted += 1
            if trips_inserted % 50_000 == 0:
                if gps_batch:
                    self.cursor.executemany(gps_query, gps_batch)
                    gps_batch.clear()
                self.db_connection.commit()
                print(f"{trips_inserted} av {len(df)} turer satt inn")

        if gps_batch:
            self.cursor.executemany(gps_query, gps_batch)

        self.db_connection.commit()
        pd.DataFrame(
            rejected_rows, columns=["csv_row", "trip_id", "reason"]
        ).to_csv("rejected_rows.csv", index=False)
        print(
            f"Ferdig: {trips_inserted} turer satt inn, "
            f"{len(rejected_rows)} rader avvist. Se rejected_rows.csv."
        )

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
