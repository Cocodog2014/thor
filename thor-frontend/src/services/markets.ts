import api from './api';
import type { PaginatedResponse, Market } from '../types';

export const marketsService = {
  async getAll() {
    const response = await api.get<PaginatedResponse<Market>>('/worldclock/markets/');
    return response.data;
  },
};

export default marketsService;
