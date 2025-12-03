--
-- PostgreSQL database dump
--

\restrict I3EWQywXFA86uySJQ3pz4q9c9EjSw39UnEzqD4pCNfoS4KpKzx5XLG4HwQ89grT

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
-- Data for Name: FutureTrading_signalstatvalue; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (1, 'STRONG_BUY', 60.000000, '2025-10-14 18:09:29.408972+00', '2025-10-14 18:09:29.408985+00', 1);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (2, 'BUY', 10.000000, '2025-10-14 18:09:29.415405+00', '2025-10-14 18:09:29.415416+00', 1);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (3, 'HOLD', 0.000000, '2025-10-14 18:09:29.420665+00', '2025-10-14 18:09:29.420677+00', 1);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (4, 'SELL', -10.000000, '2025-10-14 18:09:29.425903+00', '2025-10-14 18:09:29.425914+00', 1);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (5, 'STRONG_SELL', -60.000000, '2025-10-14 18:09:29.431379+00', '2025-10-14 18:09:29.431388+00', 1);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (6, 'STRONG_BUY', 6.000000, '2025-10-14 18:09:29.437825+00', '2025-10-14 18:09:29.437837+00', 2);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (7, 'BUY', 1.000000, '2025-10-14 18:09:29.444179+00', '2025-10-14 18:09:29.444189+00', 2);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (8, 'HOLD', 0.000000, '2025-10-14 18:09:29.448761+00', '2025-10-14 18:09:29.44877+00', 2);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (9, 'SELL', -1.000000, '2025-10-14 18:09:29.454479+00', '2025-10-14 18:09:29.454494+00', 2);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (10, 'STRONG_SELL', -6.000000, '2025-10-14 18:09:29.461425+00', '2025-10-14 18:09:29.461437+00', 2);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (11, 'STRONG_BUY', 15.000000, '2025-10-14 18:09:29.468428+00', '2025-10-14 18:09:29.46844+00', 3);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (12, 'BUY', 2.500000, '2025-10-14 18:09:29.47397+00', '2025-10-14 18:09:29.473983+00', 3);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (13, 'HOLD', 0.000000, '2025-10-14 18:09:29.478727+00', '2025-10-14 18:09:29.478736+00', 3);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (14, 'SELL', -2.500000, '2025-10-14 18:09:29.483361+00', '2025-10-14 18:09:29.483368+00', 3);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (15, 'STRONG_SELL', -15.000000, '2025-10-14 18:09:29.489404+00', '2025-10-14 18:09:29.489418+00', 3);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (16, 'STRONG_BUY', 15.000000, '2025-10-14 18:09:29.495803+00', '2025-10-14 18:09:29.495815+00', 4);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (17, 'BUY', 2.500000, '2025-10-14 18:09:29.500883+00', '2025-10-14 18:09:29.500893+00', 4);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (18, 'HOLD', 0.000000, '2025-10-14 18:09:29.507476+00', '2025-10-14 18:09:29.507488+00', 4);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (19, 'SELL', -2.500000, '2025-10-14 18:09:29.512923+00', '2025-10-14 18:09:29.512938+00', 4);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (20, 'STRONG_SELL', -15.000000, '2025-10-14 18:09:29.517769+00', '2025-10-14 18:09:29.517781+00', 4);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (21, 'STRONG_BUY', 0.300000, '2025-10-14 18:09:29.525299+00', '2025-10-14 18:09:29.525314+00', 5);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (22, 'BUY', 0.050000, '2025-10-14 18:09:29.530195+00', '2025-10-14 18:09:29.530204+00', 5);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (23, 'HOLD', 0.000000, '2025-10-14 18:09:29.535597+00', '2025-10-14 18:09:29.535606+00', 5);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (24, 'SELL', -0.050000, '2025-10-14 18:09:29.541756+00', '2025-10-14 18:09:29.54177+00', 5);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (25, 'STRONG_SELL', -0.300000, '2025-10-14 18:09:29.546732+00', '2025-10-14 18:09:29.546742+00', 5);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (26, 'STRONG_BUY', 0.060000, '2025-10-14 18:09:29.552844+00', '2025-10-14 18:09:29.552858+00', 6);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (27, 'BUY', 0.010000, '2025-10-14 18:09:29.559074+00', '2025-10-14 18:09:29.559082+00', 6);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (28, 'HOLD', 0.000000, '2025-10-14 18:09:29.565687+00', '2025-10-14 18:09:29.565702+00', 6);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (29, 'SELL', -0.010000, '2025-10-14 18:09:29.57205+00', '2025-10-14 18:09:29.572064+00', 6);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (30, 'STRONG_SELL', -0.060000, '2025-10-14 18:09:29.57757+00', '2025-10-14 18:09:29.577578+00', 6);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (31, 'STRONG_BUY', 0.012000, '2025-10-14 18:09:29.583541+00', '2025-10-14 18:09:29.583549+00', 7);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (32, 'BUY', 0.002000, '2025-10-14 18:09:29.588949+00', '2025-10-14 18:09:29.588962+00', 7);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (33, 'HOLD', 0.000000, '2025-10-14 18:09:29.594767+00', '2025-10-14 18:09:29.594778+00', 7);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (34, 'SELL', -0.002000, '2025-10-14 18:09:29.599573+00', '2025-10-14 18:09:29.59958+00', 7);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (35, 'STRONG_SELL', -0.012000, '2025-10-14 18:09:29.60488+00', '2025-10-14 18:09:29.604898+00', 7);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (36, 'STRONG_BUY', 3.000000, '2025-10-14 18:09:29.611099+00', '2025-10-14 18:09:29.611108+00', 8);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (37, 'BUY', 0.500000, '2025-10-14 18:09:29.616687+00', '2025-10-14 18:09:29.616695+00', 8);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (38, 'HOLD', 0.000000, '2025-10-14 18:09:29.625238+00', '2025-10-14 18:09:29.625252+00', 8);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (39, 'SELL', -0.500000, '2025-10-14 18:09:29.630199+00', '2025-10-14 18:09:29.630209+00', 8);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (40, 'STRONG_SELL', -3.000000, '2025-10-14 18:09:29.635471+00', '2025-10-14 18:09:29.635482+00', 8);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (41, 'STRONG_BUY', 0.100000, '2025-10-14 18:09:29.642718+00', '2025-10-14 18:09:29.642725+00', 9);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (42, 'BUY', 0.050000, '2025-10-14 18:09:29.648498+00', '2025-10-14 18:09:29.64851+00', 9);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (43, 'HOLD', 0.000000, '2025-10-14 18:09:29.653218+00', '2025-10-14 18:09:29.653229+00', 9);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (44, 'SELL', -0.050000, '2025-10-14 18:09:29.658631+00', '2025-10-14 18:09:29.658643+00', 9);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (45, 'STRONG_SELL', -0.100000, '2025-10-14 18:09:29.663631+00', '2025-10-14 18:09:29.663642+00', 9);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (46, 'STRONG_BUY', 30.000000, '2025-10-14 18:09:29.66961+00', '2025-10-14 18:09:29.66962+00', 10);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (47, 'BUY', 5.000000, '2025-10-14 18:09:29.675128+00', '2025-10-14 18:09:29.67514+00', 10);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (48, 'HOLD', 0.000000, '2025-10-14 18:09:29.679854+00', '2025-10-14 18:09:29.679861+00', 10);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (49, 'SELL', -5.000000, '2025-10-14 18:09:29.68423+00', '2025-10-14 18:09:29.684236+00', 10);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (50, 'STRONG_SELL', -30.000000, '2025-10-14 18:09:29.690525+00', '2025-10-14 18:09:29.690537+00', 10);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (51, 'STRONG_BUY', 30.000000, '2025-10-14 18:09:29.696932+00', '2025-10-14 18:09:29.696943+00', 11);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (53, 'HOLD', 0.000000, '2025-10-14 18:09:29.706924+00', '2025-10-14 18:09:29.706936+00', 11);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (54, 'SELL', -5.000000, '2025-10-14 18:09:29.71274+00', '2025-10-14 18:09:29.712754+00', 11);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (55, 'STRONG_SELL', -30.000000, '2025-10-14 18:09:29.717697+00', '2025-10-14 18:09:29.717711+00', 11);
INSERT INTO public."FutureTrading_signalstatvalue" (id, signal, value, created_at, updated_at, instrument_id) VALUES (52, 'BUY', 5.000000, '2025-10-14 18:09:29.701373+00', '2025-11-22 02:21:44.10523+00', 11);


--
-- Name: FutureTrading_signalstatvalue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."FutureTrading_signalstatvalue_id_seq"', 55, true);


--
-- PostgreSQL database dump complete
--

\unrestrict I3EWQywXFA86uySJQ3pz4q9c9EjSw39UnEzqD4pCNfoS4KpKzx5XLG4HwQ89grT

