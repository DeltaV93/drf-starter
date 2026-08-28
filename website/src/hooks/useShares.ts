import { useState, useCallback } from 'react';
import api from '../lib/api';

export interface ShareLink {
  id: number;
  token: string;
  expires_at: string | null;
  created_at: string;
}

export interface UseSharesReturn {
  shares: ShareLink[];
  loading: boolean;
  loadShares: () => Promise<void>;
  createShare: (data: {
    document_ids: number[];
    password?: string;
    expires_at?: string;
  }) => Promise<ShareLink>;
  deleteShare: (id: number) => Promise<void>;
}

export function useShares(): UseSharesReturn {
  const [shares, setShares] = useState<ShareLink[]>([]);
  const [loading, setLoading] = useState(false);

  const loadShares = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/shares/');
      setShares(response.data.data || []);
    } catch (error) {
      console.error('Failed to load shares:', error);
      setShares([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const createShare = useCallback(
    async (data: {
      document_ids: number[];
      password?: string;
      expires_at?: string;
    }) => {
      try {
        const response = await api.post('/shares/', data);
        const newShare = response.data.data;
        setShares((prev) => [...prev, newShare]);
        return newShare;
      } catch (error) {
        console.error('Failed to create share:', error);
        throw error;
      }
    },
    []
  );

  const deleteShare = useCallback(async (id: number) => {
    try {
      await api.delete(`/shares/${id}/`);
      setShares((prev) => prev.filter((share) => share.id !== id));
    } catch (error) {
      console.error('Failed to delete share:', error);
      throw error;
    }
  }, []);

  return {
    shares,
    loading,
    loadShares,
    createShare,
    deleteShare,
  };
}
