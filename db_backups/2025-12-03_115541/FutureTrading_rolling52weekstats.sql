--
-- PostgreSQL database dump
--

\restrict 6ogubYxFVLSrONt1CW0NJQgF4jHkZ573peOURRiZ9go42dGLDfMiYp8pucGgWiL

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
-- Data for Name: FutureTrading_rolling52weekstats; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (4, 'CL', 88.7000, '2025-01-15', 55.1200, '2025-04-09', 61.9900, '2025-11-17 16:33:51.304527+00', '2025-10-26 23:39:54.667115+00', 61.9900, '2025-10-27', NULL, NULL);
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (2, 'ES', 6953.7500, '2025-10-30', 4832.0000, '2025-04-07', 6873.2500, '2025-11-17 16:35:28.42012+00', '2025-10-26 23:39:54.654535+00', NULL, NULL, 6873.2500, '2025-10-26');
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (7, 'GC', 4398.0000, '2025-10-20', 2568.5000, '2024-11-18', 4082.9000, '2025-11-17 16:37:36.791668+00', '2025-10-26 23:39:54.685378+00', 4084.0000, '2025-10-26', 4082.9000, '2025-10-26');
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (6, 'HG', 5.9585, '2025-07-24', 4.0050, '2025-01-02', 5.2065, '2025-11-17 16:39:08.719596+00', '2025-10-26 23:39:54.67864+00', 5.2080, '2025-10-26', 5.2065, '2025-10-26');
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (3, 'NQ', 26399.0000, '2025-10-30', 16460.0000, '2025-04-07', 25733.5000, '2025-11-17 16:40:38.581605+00', '2025-10-26 23:39:54.659299+00', 25733.5000, '2025-10-27', 25727.0000, '2025-10-26');
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (10, 'RTY', 2566.5000, '2025-10-27', 1709.1000, '2025-04-09', 2548.3000, '2025-11-17 16:42:12.243444+00', '2025-10-26 23:42:13.458068+00', NULL, NULL, 2548.3000, '2025-10-27');
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (8, 'VX', 44.0100, '2025-04-09', 14.0100, '2024-12-13', 17.9500, '2025-11-17 16:45:28.372648+00', '2025-10-26 23:39:54.691299+00', 17.9500, '2025-10-26', NULL, NULL);
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (1, 'YM', 48528.0000, '2025-11-13', 36708.0000, '2025-04-07', 47674.0000, '2025-11-17 16:47:03.06301+00', '2025-10-26 23:39:54.647124+00', NULL, NULL, 47674.0000, '2025-10-26');
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (11, 'ZB', 122.0500, '2025-04-07', 110.0100, '2025-05-22', 118.2188, '2025-11-17 16:48:14.841539+00', '2025-10-26 23:42:13.493731+00', 118.2188, '2025-10-27', NULL, NULL);
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (9, 'DX', 98.9380, '2025-11-18', 10.7100, '2025-04-09', 98.9380, '2025-11-18 00:19:36.773068+00', '2025-10-26 23:39:54.698996+00', 98.9380, '2025-11-18', NULL, NULL);
INSERT INTO public."FutureTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (5, 'SI', 59.6450, '2025-12-03', 27.5450, '2025-04-07', 59.6450, '2025-12-03 03:29:23.540227+00', '2025-10-26 23:39:54.672805+00', 59.6450, '2025-12-03', 48.0750, '2025-10-27');


--
-- Name: FutureTrading_rolling52weekstats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."FutureTrading_rolling52weekstats_id_seq"', 11, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 6ogubYxFVLSrONt1CW0NJQgF4jHkZ573peOURRiZ9go42dGLDfMiYp8pucGgWiL

