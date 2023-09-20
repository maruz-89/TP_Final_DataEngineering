-- db init
CREATE TABLE IF NOT EXISTS public.vuelos (
	id serial4 NOT NULL,
	flight_date timestamp NOT NULL,
	flight_status varchar(20) NULL,
	departure_airport varchar(100) NULL,
	departure_timezone varchar(100) NULL,
	departure_iata varchar(5) NOT NULL,
	departure_terminal varchar(50) NULL,
	departure_delay int4 NULL,
	departure_scheduled timestamp NULL,
	arrival_airport varchar(100) NULL,
	arrival_iata varchar(5) NOT NULL,
	arrival_delay int4 NULL,
	airline_name varchar(100) NULL,
	airline_iata varchar(5) NULL,
	flight_number varchar(5) NULL,
	flight_iata varchar(10) NOT NULL,
	CONSTRAINT vuelos_pkey PRIMARY KEY (flight_date, flight_iata, departure_iata, arrival_iata)
);