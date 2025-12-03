--
-- PostgreSQL database dump
--

\restrict SI6wJginLqpSOLoANLLe6ly9P0cHu0LcUtm5CgbnHWT0m3RhlEQkoy0BDqL6phe

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
-- Data for Name: FutureTrading_instrumentcategory; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."FutureTrading_instrumentcategory" (id, name, display_name, description, is_active, sort_order, color_primary, color_secondary, created_at, updated_at) VALUES (1, 'futures', 'Futures Contracts', 'CME, CBOT, NYMEX, COMEX futures', true, 1, '#4CAF50', '#81C784', '2025-10-14 18:09:29.235417+00', '2025-11-26 14:08:24.24496+00');


--
-- Name: FutureTrading_instrumentcategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."FutureTrading_instrumentcategory_id_seq"', 1, true);


--
-- PostgreSQL database dump complete
--

\unrestrict SI6wJginLqpSOLoANLLe6ly9P0cHu0LcUtm5CgbnHWT0m3RhlEQkoy0BDqL6phe

