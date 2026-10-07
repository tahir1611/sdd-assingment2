DROP TABLE IF EXISTS GPSPoint;
DROP TABLE IF EXISTS Trip;

CREATE TABLE Trip (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id BIGINT NOT NULL,
    call_type CHAR(1),
    origin_call INT,
    origin_stand INT,
    taxi_id INT NOT NULL,
    start_time DATETIME NOT NULL,
    n_points INT,
    duration_s INT,
    distance_km DOUBLE
);

CREATE TABLE GPSPoint (
    trip_fk INT NOT NULL,
    point_no INT NOT NULL,
    longitude DOUBLE NOT NULL,
    latitude DOUBLE NOT NULL,

    PRIMARY KEY (trip_fk, point_no),

    FOREIGN KEY (trip_fk) REFERENCES Trip(id)
);