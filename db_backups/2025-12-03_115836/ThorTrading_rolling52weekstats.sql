--
-- PostgreSQL database dump
--

\restrict cVtJYPeSe8ceQhNCg4UxbZp5mi2j4pdgdFBHXprVlTgFI6Mgk2euN9JarjMauiH

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
-- Data for Name: ThorTrading_rolling52weekstats; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (4, 'RTY', 2548.3000, '2025-12-03', 2548.3000, '2025-12-03', NULL, '2025-12-03 18:45:07.890958+00', '2025-12-03 18:45:07.890972+00', NULL, NULL, NULL, NULL);
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (10, 'DX', 98.9380, '2025-12-03', 98.9380, '2025-12-03', NULL, '2025-12-03 18:45:07.934056+00', '2025-12-03 18:45:07.934072+00', NULL, NULL, NULL, NULL);
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (2, 'ES', 6869.0000, '2025-12-03', 6865.7500, '2025-12-03', 6865.7500, '2025-12-03 18:51:26.732064+00', '2025-12-03 18:45:07.87495+00', 6869.0000, '2025-12-03', 6865.7500, '2025-12-03');
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (8, 'GC', 4236.8000, '2025-12-03', 4232.6000, '2025-12-03', 4232.6000, '2025-12-03 18:51:26.76358+00', '2025-12-03 18:45:07.919615+00', 4236.8000, '2025-12-03', 4232.6000, '2025-12-03');
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (7, 'HG', 5.3930, '2025-12-03', 5.3905, '2025-12-03', 5.3930, '2025-12-03 18:47:27.090036+00', '2025-12-03 18:45:07.910423+00', 5.3930, '2025-12-03', 5.3905, '2025-12-03');
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (9, 'VX', 17.9000, '2025-12-03', 17.8000, '2025-12-03', 17.9000, '2025-12-03 18:46:40.02981+00', '2025-12-03 18:45:07.92646+00', 17.9000, '2025-12-03', 17.8000, '2025-12-03');
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (1, 'YM', 47977.0000, '2025-12-03', 47956.0000, '2025-12-03', 47956.0000, '2025-12-03 18:51:33.048292+00', '2025-12-03 18:45:07.86643+00', 47977.0000, '2025-12-03', 47956.0000, '2025-12-03');
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (6, 'SI', 58.9300, '2025-12-03', 58.8300, '2025-12-03', 58.8300, '2025-12-03 18:51:33.066107+00', '2025-12-03 18:45:07.903445+00', 58.9300, '2025-12-03', 58.8300, '2025-12-03');
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (5, 'CL', 59.1700, '2025-12-03', 59.1000, '2025-12-03', 59.1000, '2025-12-03 18:49:17.344778+00', '2025-12-03 18:45:07.896977+00', NULL, NULL, 59.1000, '2025-12-03');
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (3, 'NQ', 25653.0000, '2025-12-03', 25640.2500, '2025-12-03', 25640.2500, '2025-12-03 18:51:39.342503+00', '2025-12-03 18:45:07.88336+00', 25653.0000, '2025-12-03', 25640.2500, '2025-12-03');
INSERT INTO public."ThorTrading_rolling52weekstats" (id, symbol, high_52w, high_52w_date, low_52w, low_52w_date, last_price_checked, last_updated, created_at, all_time_high, all_time_high_date, all_time_low, all_time_low_date) VALUES (11, 'ZB', 118.2188, '2025-12-03', 118.2188, '2025-12-03', 118.2188, '2025-12-03 18:51:43.579807+00', '2025-12-03 18:45:07.941554+00', NULL, NULL, 118.2188, '2025-12-03');


--
-- Name: ThorTrading_rolling52weekstats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."ThorTrading_rolling52weekstats_id_seq"', 11, true);


--
-- PostgreSQL database dump complete
--

\unrestrict cVtJYPeSe8ceQhNCg4UxbZp5mi2j4pdgdFBHXprVlTgFI6Mgk2euN9JarjMauiH

