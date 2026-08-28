import { useState, useCallback } from 'react';
import api from '../lib/api';

export interface Document {
  id: number;
  filename: string;
  category: string;
  file_size: number;
  created_at: string;
  mime_type: string;
}

export interface DocumentVault {
  id: number;
  user: number;
  created_at: string;
  updated_at: string;
}

export interface UseDocumentsReturn {
  documents: Document[];
  vault: DocumentVault | null;
  loading: boolean;
  loadDocuments: () => Promise<void>;
  createDocument: (data: {
    filename: string;
    category: string;
    mime_type: string;
    file_size: number;
  }) => Promise<Document>;
  deleteDocument: (id: number) => Promise<void>;
  createVault: () => Promise<DocumentVault>;
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [vault, setVault] = useState<DocumentVault | null>(null);
  const [loading, setLoading] = useState(false);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/documents/documents/');
      setDocuments(response.data.data || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const createDocument = useCallback(
    async (data: {
      filename: string;
      category: string;
      mime_type: string;
      file_size: number;
    }) => {
      try {
        const response = await api.post('/documents/documents/', data);
        const newDoc = response.data.data;
        setDocuments((prev) => [...prev, newDoc]);
        return newDoc;
      } catch (error) {
        console.error('Failed to create document:', error);
        throw error;
      }
    },
    []
  );

  const deleteDocument = useCallback(async (id: number) => {
    try {
      await api.delete(`/documents/documents/${id}/`);
      setDocuments((prev) => prev.filter((doc) => doc.id !== id));
    } catch (error) {
      console.error('Failed to delete document:', error);
      throw error;
    }
  }, []);

  const createVault = useCallback(async () => {
    try {
      const response = await api.post('/documents/vault/create/', {
        key_derivation_salt: '',
        encrypted_master_key: '',
        master_key_nonce: '',
      });
      const newVault = response.data.data;
      setVault(newVault);
      return newVault;
    } catch (error) {
      console.error('Failed to create vault:', error);
      throw error;
    }
  }, []);

  return {
    documents,
    vault,
    loading,
    loadDocuments,
    createDocument,
    deleteDocument,
    createVault,
  };
}
