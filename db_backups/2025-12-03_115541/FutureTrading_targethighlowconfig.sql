--
-- PostgreSQL database dump
--

\restrict 3IBMkq59z1OAQlWG0lQFTmWbeatwfAho80zlKc7Fycc5FfiDUV3pduwjbOKPQCR

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
-- Data for Name: FutureTrading_targethighlowconfig; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (3, 'NQ', 'POINTS', 5.0000, 5.0000, NULL, NULL, true, '2025-11-22 02:10:43.898186+00', '2025-11-21 03:42:42.33464+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (1, 'YM', 'POINTS', 20.0000, 20.0000, NULL, NULL, true, '2025-11-22 02:10:43.90287+00', '2025-11-20 18:47:24.453325+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (4, 'RTY', 'POINTS', 2.0000, 2.0000, NULL, NULL, true, '2025-11-22 02:10:43.907726+00', '2025-11-21 03:43:56.292551+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (5, 'CL', 'POINTS', 0.1000, 0.1000, NULL, NULL, true, '2025-11-22 02:10:43.911798+00', '2025-11-21 03:46:11.823052+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (8, 'GC', 'POINTS', 1.0000, 1.0000, NULL, NULL, true, '2025-11-22 02:10:43.916806+00', '2025-11-21 03:49:22.394928+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (6, 'SI', 'POINTS', 0.0200, 0.0200, NULL, NULL, true, '2025-11-22 02:10:43.922189+00', '2025-11-21 03:47:13.89777+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (7, 'HG', 'POINTS', 0.0040, 0.0040, NULL, NULL, true, '2025-11-22 02:10:43.928121+00', '2025-11-21 03:48:31.278882+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (9, 'VX', 'POINTS', 0.1000, 0.1000, NULL, NULL, true, '2025-11-22 02:10:43.93225+00', '2025-11-21 03:51:15.097456+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (11, 'DX', 'POINTS', 2.0000, 2.0000, NULL, NULL, true, '2025-11-22 02:10:43.936564+00', '2025-11-21 03:55:16.824618+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (10, 'ZB', 'POINTS', 0.0938, 0.0938, NULL, NULL, true, '2025-11-22 02:10:43.940465+00', '2025-11-21 03:53:30.57458+00');
INSERT INTO public."FutureTrading_targethighlowconfig" (id, symbol, mode, offset_high, offset_low, percent_high, percent_low, is_active, updated_at, created_at) VALUES (2, 'ES', 'POINTS', 2.0000, 2.0000, NULL, NULL, true, '2025-11-22 02:11:40.384034+00', '2025-11-20 18:49:26.92761+00');


--
-- Name: FutureTrading_targethighlowconfig_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."FutureTrading_targethighlowconfig_id_seq"', 11, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 3IBMkq59z1OAQlWG0lQFTmWbeatwfAho80zlKc7Fycc5FfiDUV3pduwjbOKPQCR

