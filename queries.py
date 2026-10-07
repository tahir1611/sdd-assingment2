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

        print(tabulate(rows, headers=self.cursor.column_names))


def main():
    program = None

    try:
        program = Queries()
        program.query_1()

    except Exception as e:
        print("ERROR:", e)

    finally:
        if program:
            program.connection.close_connection()


if __name__ == "__main__":
    main()