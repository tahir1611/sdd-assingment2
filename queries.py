from DbConnector import DbConnector
from tabulate import tabulate


class Queries:

    def __init__(self):
        self.connection = DbConnector()
        self.cursor = self.connection.cursor

    def query_1(self):
        query = """
        SELECT
            COUNT(DISTINCT taxi_id) AS number_of_taxis,
            COUNT(*) AS number_of_trips,
            SUM(n_points) AS total_gps_points
        FROM Trip;
        """

        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


    def query_2(self):
        query = """
            SELECT AVG(number_of_trips) AS average_trips_per_taxi
            FROM (
                SELECT Taxi_id, COUNT(*) AS number_of_trips
                FROM Trip
                GROUP BY Taxi_id
            ) AS trips_per_taxi;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


    def query_3(self):
        query = """
            SELECT Taxi_id, COUNT(*) AS number_of_trips
            FROM Trip
            GROUP BY Taxi_id
            ORDER BY number_of_trips DESC
            LIMIT 20
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


    def query_4(self):
        query = """
            SELECT
                Taxi_id,
                CALL_TYPE,
                COUNT(*) AS number_of_trips
            FROM Trip
            GROUP BY Taxi_id, CALL_TYPE;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


    def query_5(self):
        query = """
            SELECT
                CALL_TYPE,
                AVG(duration) AS avg_duration,
                AVG(distance) AS avg_distance,
                AVG(CASE WHEN HOUR(start_time) < 6 THEN 1 ELSE 0 END) AS share_00_06,
                AVG(CASE WHEN HOUR(start_time) < 12 AND HOUR(start_time) >= 6 THEN 1 ELSE 0 END) AS share_06_12,
                AVG(CASE WHEN HOUR(start_time) < 18 AND HOUR(start_time) >= 12 THEN 1 ELSE 0 END) AS share_12_18,
                AVG(CASE WHEN HOUR(start_time) >= 18 THEN 1 ELSE 0 END) AS share_18_24
            FROM Trip
            GROUP BY CALL_TYPE;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


        def query_6(self):
            query = """
                SELECT
                    Taxi_id,
                    SUM(duration) / 3600 AS total_hours,
                    SUM(distance) AS total_distance
                FROM Trip
                GROUP BY Taxi_id
                ORDER BY total_hours DESC;
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


        def query_7(self):
            query = """
                SELECT DISTINCT t.id
                FROM Trip t
                WHERE EXISTS (
                    SELECT 1
                    FROM TrackPoint p
                    WHERE p.trip_id = t.id
                    AND ST_Distance_Sphere(
                            POINT(p.longitude, p.latitude),
                            POINT(-8.62911, 41.15794)
                        ) <= 100
                );
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


        def query_8(self):
            query = """
                SELECT COUNT(*) AS invalid_trips
                FROM (
                    SELECT t.id
                    FROM Trip t
                    LEFT JOIN TrackPoint p
                        ON p.trip_id = t.id
                    GROUP BY t.id
                    HAVING COUNT(p.id) < 3
                ) AS invalid;
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


        def query_9(self):
            query = """
                SELECT *
                FROM Trip
                WHERE DATE(end_time) = DATE(start_time) + INTERVAL 1 DAY;
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


        def query_10(self):
            query = """
                SELECT *
                FROM Trip
                WHERE ST_Distance_Sphere(
                    POINT(start_longitude, start_latitude),
                    POINT(end_longitude, end_latitude)
                ) <= 50;
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


        def query_11(self):
            query = """
                SELECT
                    Taxi_id,
                    AVG(TIMESTAMPDIFF(MINUTE, prev_end, start_time)) AS avg_idle_minutes
                FROM (
                    SELECT
                        Taxi_id,
                        start_time,
                        LAG(end_time) OVER (
                            PARTITION BY Taxi_id
                            ORDER BY start_time
                        ) AS prev_end
                    FROM Trip
                ) t
                WHERE prev_end IS NOT NULL
                GROUP BY Taxi_id;
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


def main():
    program = None

    try:
        program = Queries()
        for i in range(1, 4):
            query = getattr(program, f"query_{i}")
            query()
    except Exception as e:
        print("ERROR:", e)

    finally:
        if program:
            program.connection.close_connection()


if __name__ == "__main__":
    main()