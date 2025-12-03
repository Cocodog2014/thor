--
-- PostgreSQL database dump
--

\restrict LA9SuCOMLiIMbvaK69G9JRY7xxMvNCK1tAdNYeLPtklcrWL0ddayD81EzzcMKY9

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
-- Data for Name: FutureTrading_tradinginstrument; Type: TABLE DATA; Schema: public; Owner: thor_user
--

INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (1, '/YM', 'E-mini Dow Futures', '', 'CBOT', 'USD', true, true, 0, 0, 1.000000, 5.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.272831+00', '2025-12-02 18:48:49.443426+00', 1, 5.00, 17000.01, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (5, '/CL', 'Crude Oil Futures', '', 'NYMEX', 'USD', true, true, 0, 2, 0.010000, 1000.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.326231+00', '2025-12-02 18:55:08.380343+00', 1, 10.00, 8786.00, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (10, '/DX', 'US Dollar Index Futures', '', 'ICE', 'USD', true, true, 0, 2, 0.010000, 10.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.386609+00', '2025-12-02 18:55:08.383831+00', 1, 0.10, 2500.00, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (2, '/ES', 'E-mini S&P 500 Futures', '', 'CME', 'USD', true, true, 0, 2, 0.250000, 50.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.287615+00', '2025-12-02 18:55:08.386241+00', 1, 12.50, 24000.00, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (8, '/GC', 'Gold Futures', '', 'COMEX', 'USD', true, true, 0, 1, 0.100000, 100.00, 'thinkorswim_rtd', 'TOS', 5, NULL, false, '2025-10-14 18:09:29.364949+00', '2025-12-02 18:55:08.388472+00', 1, 10.00, 32110.00, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (7, '/HG', 'Copper', '', 'COMEX', 'USD', true, true, 0, 4, 0.000500, 25000.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.351457+00', '2025-12-02 18:55:08.390452+00', 1, 12.50, 4000.00, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (3, '/NQ', 'E-mini Nasdaq 100 Futures', '', 'CME', 'USD', true, true, 0, 2, 0.250000, 20.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.300678+00', '2025-12-02 18:55:08.392439+00', 1, 5.00, 16000.00, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (4, '/RTY', 'E-mini Russell 2000 Futures', '', 'CME', 'USD', true, true, 0, 1, 0.100000, 50.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.313872+00', '2025-12-02 18:55:08.394505+00', 1, 5.00, 11037.00, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (6, '/SI', 'Silver Futures', '', 'COMEX', 'USD', true, true, 0, 3, 0.005000, 5000.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.337436+00', '2025-12-02 18:55:08.39675+00', 1, 25.00, 32000.00, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (9, '/VX', 'VIX Futures', '', 'CFE', 'USD', true, true, 0, 2, 0.050000, 1000.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.376316+00', '2025-12-02 18:55:08.398816+00', 1, 50.00, 19996.90, true);
INSERT INTO public."FutureTrading_tradinginstrument" (id, symbol, name, description, exchange, currency, is_active, is_watchlist, sort_order, display_precision, tick_size, contract_size, api_provider, api_symbol, update_frequency, last_updated, is_market_open, created_at, updated_at, category_id, tick_value, margin_requirement, show_in_ribbon) VALUES (11, '/ZB', '30-Year T-Bond Futures', '', 'CBOT', 'USD', true, true, 0, 3, 0.031250, 1000.00, '', '', 5, NULL, false, '2025-10-14 18:09:29.396819+00', '2025-12-02 18:55:08.401363+00', 1, 31.25, 5000.00, true);


--
-- Name: FutureTrading_tradinginstrument_id_seq; Type: SEQUENCE SET; Schema: public; Owner: thor_user
--

SELECT pg_catalog.setval('public."FutureTrading_tradinginstrument_id_seq"', 11, true);


--
-- PostgreSQL database dump complete
--

\unrestrict LA9SuCOMLiIMbvaK69G9JRY7xxMvNCK1tAdNYeLPtklcrWL0ddayD81EzzcMKY9

