--
-- PostgreSQL database dump
--

\restrict EJ1FWMSK2kESQGL9ARpOYE7cc8ZgVveQvnS8KG6P0peanGQ8lyCSSJ2Ar9aJOBR

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: GlobalMarkets_market; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (2, 'Japan', 'Asia/Tokyo', '09:00:00', '15:00:00', 'CLOSED', true, '', '2025-12-03 19:29:15.478523+00', '2025-12-03 19:29:15.478545+00', true, 0.10, true, true, true);
INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (3, 'China', 'Asia/Shanghai', '09:30:00', '15:00:00', 'CLOSED', true, '', '2025-12-03 19:29:15.487+00', '2025-12-03 19:29:15.487011+00', true, 0.10, true, true, true);
INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (4, 'India', 'Asia/Kolkata', '09:15:00', '15:30:00', 'CLOSED', true, '', '2025-12-03 19:29:15.493969+00', '2025-12-03 19:29:15.493984+00', true, 0.10, true, true, true);
INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (5, 'Germany', 'Europe/Berlin', '09:00:00', '17:30:00', 'CLOSED', true, '', '2025-12-03 19:29:15.501881+00', '2025-12-03 19:29:15.501893+00', true, 0.10, true, false, false);
INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (6, 'United Kingdom', 'Europe/London', '08:00:00', '16:30:00', 'CLOSED', true, '', '2025-12-03 19:29:15.509782+00', '2025-12-03 19:29:15.509792+00', true, 0.10, true, true, true);
INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (7, 'Pre-USA', 'America/New_York', '06:00:00', '09:30:00', 'CLOSED', true, '', '2025-12-03 19:29:15.517897+00', '2025-12-03 19:29:15.517908+00', true, 0.10, true, true, true);
INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (9, 'Canada', 'America/Toronto', '09:30:00', '16:00:00', 'OPEN', true, '', '2025-12-03 19:29:15.531753+00', '2025-12-03 19:30:08.377994+00', true, 0.10, true, false, false);
INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (10, 'Mexico', 'America/Mexico_City', '08:30:00', '15:00:00', 'OPEN', true, '', '2025-12-03 19:29:15.5391+00', '2025-12-03 19:30:08.388855+00', true, 0.10, true, false, false);
INSERT INTO public."GlobalMarkets_market" (id, country, timezone_name, market_open_time, market_close_time, status, is_active, currency, created_at, updated_at, is_control_market, weight, enable_close_capture, enable_futures_capture, enable_open_capture) VALUES (8, 'United States', 'America/New_York', '09:30:00', '16:00:00', 'OPEN', true, '', '2025-12-03 19:29:15.525345+00', '2025-12-03 19:30:08.39383+00', true, 0.20, true, true, true);


--
-- Name: GlobalMarkets_market_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."GlobalMarkets_market_id_seq"', 10, true);


--
-- PostgreSQL database dump complete
--

\unrestrict EJ1FWMSK2kESQGL9ARpOYE7cc8ZgVveQvnS8KG6P0peanGQ8lyCSSJ2Ar9aJOBR

