/**
 * useAgentStorage — Hook d'accès au stockage MinIO d'un agent.
 *
 * Fournit des méthodes pour uploader, télécharger et lister les fichiers
 * dans l'espace de stockage dédié à l'agent.
 *
 * Supporte deux modes de stockage:
 * - Utilisateur (par défaut): users/{user_id}/agents/{slug}/
 * - Workspace (collaboratif): workspaces/{workspace_id}/agents/{slug}/
 */

import { useCallback, useState } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || '';

interface StorageFile {
  key: string;
  filename: string;
  size_bytes: number;
  content_type: string;
}

interface UseAgentStorageOptions {
  /** ID du workspace pour le stockage collaboratif */
  workspaceId?: string | null;
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

export function useAgentStorage(
  agentSlug: string,
  options: UseAgentStorageOptions = {}
): UseAgentStorageReturn {
  const { workspaceId } = options;
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return { Authorization: `Bearer ${token}` };
  };

  /** Append workspace_id query param if present */
  const wsParam = (existing: string) => {
    if (!workspaceId) return existing;
    const sep = existing.includes('?') ? '&' : '?';
    return `${existing}${sep}workspace_id=${encodeURIComponent(workspaceId)}`;
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

        let url = `${API_BASE}/api/agent-runtime/${agentSlug}/storage/upload`;
        if (workspaceId) url += `?workspace_id=${encodeURIComponent(workspaceId)}`;

        const response = await fetch(url, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData,
        });

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
    [agentSlug, workspaceId]
  );

  const download = useCallback(
    async (key: string): Promise<Blob> => {
      let url = `${API_BASE}/api/agent-runtime/${agentSlug}/storage/download?key=${encodeURIComponent(key)}`;
      url = wsParam(url);

      const response = await fetch(url, { headers: getAuthHeaders() });
      if (!response.ok) throw new Error('Fichier introuvable');
      return response.blob();
    },
    [agentSlug, workspaceId]
  );

  const listFiles = useCallback(
    async (prefix?: string): Promise<StorageFile[]> => {
      let url = `${API_BASE}/api/agent-runtime/${agentSlug}/storage/list`;
      const params: string[] = [];
      if (prefix) params.push(`prefix=${encodeURIComponent(prefix)}`);
      if (workspaceId) params.push(`workspace_id=${encodeURIComponent(workspaceId)}`);
      if (params.length) url += `?${params.join('&')}`;

      const response = await fetch(url, { headers: getAuthHeaders() });
      if (!response.ok) throw new Error('Erreur de listing');
      return response.json();
    },
    [agentSlug, workspaceId]
  );

  const deleteFile = useCallback(
    async (key: string): Promise<boolean> => {
      const response = await fetch(
        `${API_BASE}/api/agent-runtime/${agentSlug}/storage/delete`,
        {
          method: 'DELETE',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ key, workspace_id: workspaceId || undefined }),
        }
      );

      return response.ok;
    },
    [agentSlug, workspaceId]
  );

  return { upload, download, listFiles, deleteFile, isUploading, uploadProgress, error };
}
