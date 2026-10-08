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

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".2f"))


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


    # Oppgave 4a: mest brukte call_type per taxi
    def query_4(self):
        query = """
            SELECT Taxi_id, call_type AS most_used_call_type, number_of_trips
            FROM (
                SELECT
                    Taxi_id,
                    call_type,
                    COUNT(*) AS number_of_trips,
                    ROW_NUMBER() OVER (
                        PARTITION BY Taxi_id
                        ORDER BY COUNT(*) DESC, call_type
                    ) AS rank_in_taxi
                FROM Trip
                GROUP BY Taxi_id, call_type
            ) AS ranked
            WHERE rank_in_taxi = 1
            ORDER BY Taxi_id;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        # 448 taxier: vis de 20 første og en oppsummering
        print(tabulate(rows[:20], headers=self.cursor.column_names, floatfmt=".0f"))
        print(f"... {len(rows)} taxier totalt")
        summary = {}
        for _, call_type, _ in rows:
            summary[call_type] = summary.get(call_type, 0) + 1
        print(tabulate(sorted(summary.items()), headers=["most_used_call_type", "taxis"]))


    # Oppgave 4b: snittvarighet, snittdistanse og andel turer per tidsintervall
    def query_5(self):
        query = """
            SELECT
                call_type,
                COUNT(*) AS trips,
                AVG(duration_s) / 60 AS avg_duration_min,
                AVG(distance_km) AS avg_distance_km,
                100 * AVG(CASE WHEN HOUR(start_time) < 6 THEN 1 ELSE 0 END) AS pct_00_06,
                100 * AVG(CASE WHEN HOUR(start_time) >= 6 AND HOUR(start_time) < 12 THEN 1 ELSE 0 END) AS pct_06_12,
                100 * AVG(CASE WHEN HOUR(start_time) >= 12 AND HOUR(start_time) < 18 THEN 1 ELSE 0 END) AS pct_12_18,
                100 * AVG(CASE WHEN HOUR(start_time) >= 18 THEN 1 ELSE 0 END) AS pct_18_24
            FROM Trip
            WHERE n_points >= 3
            GROUP BY call_type
            ORDER BY call_type;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".2f"))


    # Oppgave 5: taxier med flest timer kjørt, og total distanse
    def query_6(self):
        query = """
            SELECT
                Taxi_id,
                SUM(duration_s) / 3600 AS total_hours,
                SUM(distance_km) AS total_distance_km
            FROM Trip
            WHERE n_points >= 3
            GROUP BY Taxi_id
            ORDER BY total_hours DESC;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".2f"))


    # Oppgave 6: turer som passerte innenfor 100 m fra Porto rådhus
    def query_7(self):
        # BETWEEN er et grovt rektangel litt større enn 100 m rundt rådhuset,
        # så avstanden bare regnes ut for punktene i nærheten.
        query = """
            SELECT t.trip_id, t.Taxi_id, t.start_time, near.min_distance_m
            FROM (
                SELECT
                    p.trip_fk,
                    MIN(ST_Distance_Sphere(
                        POINT(p.longitude, p.latitude),
                        POINT(-8.62911, 41.15794)
                    )) AS min_distance_m
                FROM GPSPoint p
                WHERE p.latitude BETWEEN 41.15794 - 0.001 AND 41.15794 + 0.001
                  AND p.longitude BETWEEN -8.62911 - 0.0013 AND -8.62911 + 0.0013
                GROUP BY p.trip_fk
                HAVING min_distance_m <= 100
            ) AS near
            JOIN Trip t ON t.id = near.trip_fk
            ORDER BY near.min_distance_m;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows[:20], headers=self.cursor.column_names, floatfmt=".1f"))
        print(f"... {len(rows)} turer totalt")


    # Oppgave 7: ugyldige turer (færre enn 3 GPS-punkter)
    def query_8(self):
        query = """
            SELECT
                COUNT(*) AS invalid_trips,
                SUM(n_points = 0) AS with_0_points,
                SUM(n_points = 1) AS with_1_point,
                SUM(n_points = 2) AS with_2_points
            FROM Trip
            WHERE n_points < 3;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".0f"))


    # Oppgave 8: turer som startet én dag og sluttet neste dag
    def query_9(self):
        query = """
            SELECT
                trip_id,
                Taxi_id,
                start_time,
                start_time + INTERVAL duration_s SECOND AS end_time
            FROM Trip
            WHERE n_points >= 3
              AND DATE(start_time + INTERVAL duration_s SECOND) = DATE(start_time) + INTERVAL 1 DAY
            ORDER BY start_time;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows[:20], headers=self.cursor.column_names))
        print(f"... {len(rows)} turer totalt")


    # Oppgave 9: rundturer (start og slutt innenfor 50 m)
    def query_10(self):
        query = """
            SELECT
                t.trip_id,
                t.Taxi_id,
                t.distance_km,
                ST_Distance_Sphere(
                    POINT(s.longitude, s.latitude),
                    POINT(e.longitude, e.latitude)
                ) AS start_end_distance_m
            FROM Trip t
            JOIN GPSPoint s ON s.trip_fk = t.id AND s.point_no = 0
            JOIN GPSPoint e ON e.trip_fk = t.id AND e.point_no = t.n_points - 1
            WHERE t.n_points >= 3
              AND ST_Distance_Sphere(
                    POINT(s.longitude, s.latitude),
                    POINT(e.longitude, e.latitude)
                  ) <= 50
            ORDER BY t.distance_km DESC;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows[:20], headers=self.cursor.column_names, floatfmt=".2f"))
        print(f"... {len(rows)} turer totalt")


    # Oppgave 10: gjennomsnittlig ventetid mellom turer, topp 20 taxier
    def query_11(self):
        # Ventetid = start på en tur minus slutt på forrige tur for samme taxi.
        # Negative verdier betyr at turene overlapper, og de er ikke ventetid.
        query = """
            SELECT
                Taxi_id,
                COUNT(*) AS gaps,
                AVG(idle_minutes) AS avg_idle_minutes
            FROM (
                SELECT
                    Taxi_id,
                    TIMESTAMPDIFF(SECOND, prev_end, start_time) / 60 AS idle_minutes
                FROM (
                    SELECT
                        Taxi_id,
                        start_time,
                        LAG(start_time + INTERVAL duration_s SECOND) OVER (
                            PARTITION BY Taxi_id
                            ORDER BY start_time, id
                        ) AS prev_end
                    FROM Trip
                ) AS ordered
                WHERE prev_end IS NOT NULL
            ) AS gaps
            WHERE idle_minutes >= 0
            GROUP BY Taxi_id
            ORDER BY avg_idle_minutes DESC
            LIMIT 20;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        print(tabulate(rows, headers=self.cursor.column_names, floatfmt=".1f"))


def main():
    program = None

    try:
        program = Queries()
        for i in range(1, 12):
            print(f"\n=== query_{i} ===")
            query = getattr(program, f"query_{i}")
            query()
    except Exception as e:
        print("ERROR:", e)

    finally:
        if program:
            program.connection.close_connection()


if __name__ == "__main__":
    main()
