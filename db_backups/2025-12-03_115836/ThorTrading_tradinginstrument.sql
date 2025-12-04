--
-- PostgreSQL database dump
--

\restrict urevhX3DSvc3qoYIMxzL5uhigQpI4CaYWoHCMPPacf3jp0T4u862pldhto1bOAT

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
-- Data for Name: ThorTrading_tradinginstrument; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (1, '/ES', 'E-mini S&P 500 Futures', '', 'CME', 'USD', true, true, 0, 2, 0.250000, 50.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.163448+00', '2025-12-03 18:38:54.163461+00', 1, NULL, 12.50);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (2, '/NQ', 'E-mini Nasdaq 100 Futures', '', 'CME', 'USD', true, true, 0, 2, 0.250000, 20.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.170737+00', '2025-12-03 18:38:54.170752+00', 1, NULL, 5.00);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (3, '/YM', 'E-mini Dow Futures', '', 'CBOT', 'USD', true, true, 0, 0, 1.000000, 5.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.17621+00', '2025-12-03 18:38:54.176223+00', 1, NULL, 5.00);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (4, '/RTY', 'E-mini Russell 2000 Futures', '', 'CME', 'USD', true, true, 0, 1, 0.100000, 50.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.182462+00', '2025-12-03 18:38:54.182475+00', 1, NULL, 5.00);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (5, '/CL', 'Crude Oil Futures', '', 'NYMEX', 'USD', true, true, 0, 2, 0.010000, 1000.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.189776+00', '2025-12-03 18:38:54.18979+00', 1, NULL, 10.00);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (6, '/GC', 'Gold Futures', '', 'COMEX', 'USD', true, true, 0, 1, 0.100000, 100.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.195481+00', '2025-12-03 18:38:54.195493+00', 1, NULL, 10.00);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (7, '/SI', 'Silver Futures', '', 'COMEX', 'USD', true, true, 0, 3, 0.005000, 5000.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.200966+00', '2025-12-03 18:38:54.200979+00', 1, NULL, 25.00);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (8, '/HG', 'Copper Futures', '', 'COMEX', 'USD', true, true, 0, 4, 0.000500, 25000.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.208265+00', '2025-12-03 18:38:54.208278+00', 1, NULL, 12.50);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (9, '/VX', 'VIX Futures', '', 'CFE', 'USD', true, true, 0, 2, 0.050000, 1000.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.213307+00', '2025-12-03 18:38:54.213315+00', 1, NULL, 50.00);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (10, '/DX', 'US Dollar Index Futures', '', 'ICE', 'USD', true, true, 0, 2, 0.010000, 10.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.220759+00', '2025-12-03 18:38:54.220772+00', 1, NULL, 0.10);
INSERT INTO public."ThorTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, margin_requirement, tick_value) VALUES (11, '/ZB', '30-Year T-Bond Futures', '', 'CBOT', 'USD', true, true, 0, 3, 0.031250, 1000.00, '', '', 5, NULL, false, '2025-12-03 18:38:54.226652+00', '2025-12-03 18:38:54.226665+00', 1, NULL, 31.25);


--
-- Name: ThorTrading_tradinginstrument_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."ThorTrading_tradinginstrument_id_seq"', 11, true);


--
-- PostgreSQL database dump complete
--

\unrestrict urevhX3DSvc3qoYIMxzL5uhigQpI4CaYWoHCMPPacf3jp0T4u862pldhto1bOAT

