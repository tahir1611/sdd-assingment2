CREATE TABLE Trip (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trip_id BIGINT NOT NULL,
    call_type CHAR(1),
    origin_call INT,
    origin_stand INT,
    taxi_id INT NOT NULL,
    start_time DATETIME NOT NULL,
    day_type CHAR(1),
    n_points INT,
    duration_s INT,
    distance_km DOUBLE
);

CREATE TABLE GPSPoint (
    trip_fk BIGINT NOT NULL,
    point_no INT NOT NULL,
    longitude DOUBLE NOT NULL,
    latitude DOUBLE NOT NULL,

    PRIMARY KEY (trip_fk, point_no),

    FOREIGN KEY (trip_fk) REFERENCES Trip(id)
);