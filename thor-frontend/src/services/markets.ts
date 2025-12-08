import api from './api';
import type { PaginatedResponse, Market } from '../types';

export const marketsService = {
  async getAll() {
    // Use the preferred alias; backend also keeps /worldclock/ for legacy
    const response = await api.get<PaginatedResponse<Market>>('/global-markets/markets/', {
      timeout: 20000, // allow up to 20s for the heavier schedule payload
    });
    return response.data;
  },
};

export default marketsService;
