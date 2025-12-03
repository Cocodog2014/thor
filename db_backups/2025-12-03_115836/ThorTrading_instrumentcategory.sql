--
-- PostgreSQL database dump
--

\restrict AU0d8UavJhlu7YF2RQ1AahWZtGwmCrfGmQFqLbkjZplPrHXgJiChycxmalrpz91

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
-- Data for Name: ThorTrading_instrumentcategory; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."ThorTrading_instrumentcategory" (id, name, display_name, description, is_active, sort_order, color_primary, color_secondary, created_at, updated_at) VALUES (1, 'futures', 'Futures Contracts', 'CME, CBOT, NYMEX, COMEX futures', true, 1, '#4CAF50', '#81C784', '2025-12-03 18:38:54.156948+00', '2025-12-03 18:38:54.156965+00');


--
-- Name: ThorTrading_instrumentcategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."ThorTrading_instrumentcategory_id_seq"', 1, true);


--
-- PostgreSQL database dump complete
--

\unrestrict AU0d8UavJhlu7YF2RQ1AahWZtGwmCrfGmQFqLbkjZplPrHXgJiChycxmalrpz91

