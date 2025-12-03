--
-- PostgreSQL database dump
--

\restrict U1IETJ6j6uhuYvRrqXrAPcG95xbqIRnDKr3UzgaxwzayViyA9SR7BaoOAJLNysK

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
-- Data for Name: ThorTrading_targethighlowconfig; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (1, 'ES', 'POINTS', 2.0000, 2.0000, NULL, NULL, true, '2025-12-03 18:38:54.311281+00', '2025-12-03 18:38:54.311298+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (2, 'NQ', 'POINTS', 5.0000, 5.0000, NULL, NULL, true, '2025-12-03 18:38:54.316761+00', '2025-12-03 18:38:54.316776+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (3, 'YM', 'POINTS', 20.0000, 20.0000, NULL, NULL, true, '2025-12-03 18:38:54.322278+00', '2025-12-03 18:38:54.322289+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (4, 'RTY', 'POINTS', 2.0000, 2.0000, NULL, NULL, true, '2025-12-03 18:38:54.327763+00', '2025-12-03 18:38:54.327779+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (5, 'CL', 'POINTS', 0.1000, 0.1000, NULL, NULL, true, '2025-12-03 18:38:54.334586+00', '2025-12-03 18:38:54.334602+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (6, 'GC', 'POINTS', 1.0000, 1.0000, NULL, NULL, true, '2025-12-03 18:38:54.341666+00', '2025-12-03 18:38:54.34168+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (7, 'SI', 'POINTS', 0.0200, 0.0200, NULL, NULL, true, '2025-12-03 18:38:54.347539+00', '2025-12-03 18:38:54.347555+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (8, 'HG', 'POINTS', 0.0040, 0.0040, NULL, NULL, true, '2025-12-03 18:38:54.353516+00', '2025-12-03 18:38:54.35353+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (9, 'VX', 'POINTS', 0.1000, 0.1000, NULL, NULL, true, '2025-12-03 18:38:54.359312+00', '2025-12-03 18:38:54.359321+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (10, 'DX', 'POINTS', 2.0000, 2.0000, NULL, NULL, true, '2025-12-03 18:38:54.366442+00', '2025-12-03 18:38:54.366457+00');
INSERT INTO public."ThorTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (11, 'ZB', 'POINTS', 0.0938, 0.0938, NULL, NULL, true, '2025-12-03 18:38:54.372703+00', '2025-12-03 18:38:54.372719+00');


--
-- Name: ThorTrading_targethighlowconfig_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."ThorTrading_targethighlowconfig_id_seq"', 11, true);


--
-- PostgreSQL database dump complete
--

\unrestrict U1IETJ6j6uhuYvRrqXrAPcG95xbqIRnDKr3UzgaxwzayViyA9SR7BaoOAJLNysK

