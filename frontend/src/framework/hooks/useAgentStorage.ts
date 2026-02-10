/**
 * useAgentStorage — Hook d'accès au stockage MinIO d'un agent.
 *
 * Fournit des méthodes pour uploader, télécharger et lister les fichiers
 * dans l'espace de stockage dédié à l'agent + utilisateur courant.
 */

import { useCallback, useState } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || '/api';

interface StorageFile {
  key: string;
  filename: string;
  size_bytes: number;
  content_type: string;
}

interface UseAgentStorageReturn {
  /** Upload un fichier */
  upload: (file: File, path?: string) => Promise<string>;
  /** Télécharge un fichier */
  download: (key: string) => Promise<Blob>;
  /** Liste les fichiers */
  listFiles: (prefix?: string) => Promise<StorageFile[]>;
  /** Supprime un fichier */
  deleteFile: (key: string) => Promise<boolean>;
  /** Upload en cours */
  isUploading: boolean;
  /** Progression de l'upload (0-100) */
  uploadProgress: number;
  /** Erreur éventuelle */
  error: string | null;
}

export function useAgentStorage(agentSlug: string): UseAgentStorageReturn {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return { Authorization: `Bearer ${token}` };
  };

  const upload = useCallback(
    async (file: File, path?: string): Promise<string> => {
      setIsUploading(true);
      setUploadProgress(0);
      setError(null);

      try {
        const formData = new FormData();
        formData.append('file', file);
        if (path) formData.append('path', path);

        const response = await fetch(
          `${API_BASE}/agent-runtime/${agentSlug}/storage/upload`,
          {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData,
          }
        );

        if (!response.ok) throw new Error('Erreur d\'upload');

        const data = await response.json();
        setUploadProgress(100);
        return data.key;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erreur d\'upload';
        setError(message);
        throw err;
      } finally {
        setIsUploading(false);
      }
    },
    [agentSlug]
  );

  const download = useCallback(
    async (key: string): Promise<Blob> => {
      const response = await fetch(
        `${API_BASE}/agent-runtime/${agentSlug}/storage/download?key=${encodeURIComponent(key)}`,
        { headers: getAuthHeaders() }
      );

      if (!response.ok) throw new Error('Fichier introuvable');
      return response.blob();
    },
    [agentSlug]
  );

  const listFiles = useCallback(
    async (prefix?: string): Promise<StorageFile[]> => {
      const params = prefix ? `?prefix=${encodeURIComponent(prefix)}` : '';
      const response = await fetch(
        `${API_BASE}/agent-runtime/${agentSlug}/storage/list${params}`,
        { headers: getAuthHeaders() }
      );

      if (!response.ok) throw new Error('Erreur de listing');
      return response.json();
    },
    [agentSlug]
  );

  const deleteFile = useCallback(
    async (key: string): Promise<boolean> => {
      const response = await fetch(
        `${API_BASE}/agent-runtime/${agentSlug}/storage/delete`,
        {
          method: 'DELETE',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ key }),
        }
      );

      return response.ok;
    },
    [agentSlug]
  );

  return { upload, download, listFiles, deleteFile, isUploading, uploadProgress, error };
}
