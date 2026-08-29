import { useState, useCallback } from 'react';
import { apiData } from '../lib/api';
import { routes } from '../lib/routes';

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
  }) => Promise<ShareLink | undefined>;
  deleteShare: (id: number) => Promise<void>;
}

export function useShares(): UseSharesReturn {
  const [shares, setShares] = useState<ShareLink[]>([]);
  const [loading, setLoading] = useState(false);

  const loadShares = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiData<ShareLink[]>({ url: routes.api.shares.list(), method: 'GET' });
      setShares(data || []);
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
        const newShare = await apiData<ShareLink>({
          url: routes.api.shares.list(),
          method: 'POST',
          data,
        });
        if (newShare) setShares((prev) => [...prev, newShare]);
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
      await apiData({
        url: routes.api.shares.detail(id),
        method: 'DELETE',
      });
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
