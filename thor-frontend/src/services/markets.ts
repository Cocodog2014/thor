import api from './api';
import type { Market } from '../types';

export const marketsService = {
  async getAll() {
    const response = await api.get<Market[]>('/global-markets/markets/', {
      timeout: 10000,
    });
    return response.data;
  },
};

export default marketsService;
