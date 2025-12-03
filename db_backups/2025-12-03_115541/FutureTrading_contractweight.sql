--
-- PostgreSQL database dump
--

\restrict NRfAQ302gh4QX26xNIN25z0YaacdYhWVGPfrbOgSBsVUBdEWlKDKIFiAcik6T71

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
-- Data for Name: FutureTrading_contractweight; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (1, 55.000000, '2025-10-14 18:09:29.280836+00', '2025-10-20 02:00:25.829413+00', 1);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (2, 6.000000, '2025-10-14 18:09:29.293625+00', '2025-10-20 02:00:25.835213+00', 2);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (3, 15.000000, '2025-10-14 18:09:29.308376+00', '2025-10-20 02:00:25.841421+00', 3);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (4, 15.000000, '2025-10-14 18:09:29.320619+00', '2025-10-20 02:00:25.847111+00', 4);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (5, 0.300000, '2025-10-14 18:09:29.331552+00', '2025-10-20 02:00:25.852728+00', 5);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (6, 0.060000, '2025-10-14 18:09:29.343038+00', '2025-10-20 02:00:25.858387+00', 6);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (7, 0.012000, '2025-10-14 18:09:29.359277+00', '2025-10-20 02:00:25.863429+00', 7);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (8, 4.000000, '2025-10-14 18:09:29.370017+00', '2025-10-20 02:00:25.868971+00', 8);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (9, 0.300000, '2025-10-14 18:09:29.381453+00', '2025-10-20 02:00:25.874677+00', 9);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (10, 35.000000, '2025-10-14 18:09:29.39196+00', '2025-10-20 02:00:25.879433+00', 10);
INSERT INTO public."FutureTrading_contractweight" (id, weight, created_at, updated_at, instrument_id) VALUES (11, 35.000000, '2025-10-14 18:09:29.401884+00', '2025-10-20 02:00:25.884106+00', 11);


--
-- Name: FutureTrading_contractweight_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."FutureTrading_contractweight_id_seq"', 11, true);


--
-- PostgreSQL database dump complete
--

\unrestrict NRfAQ302gh4QX26xNIN25z0YaacdYhWVGPfrbOgSBsVUBdEWlKDKIFiAcik6T71

