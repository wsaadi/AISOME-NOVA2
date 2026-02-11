/**
 * FileUpload — Composant d'upload de fichiers pour les agents.
 *
 * Usage:
 *   import { FileUpload } from 'framework/components';
 *   <FileUpload onUpload={(file) => handleFile(file)} accept=".pdf,.docx" />
 */

import React, { useCallback, useRef, useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteIcon from '@mui/icons-material/Delete';

interface UploadedFile {
  file: File;
  key?: string;
  progress: number;
  error?: string;
}

interface FileUploadProps {
  /** Callback quand un fichier est uploadé */
  onUpload: (file: File) => Promise<string>;
  /** Types de fichiers acceptés */
  accept?: string;
  /** Upload multiple */
  multiple?: boolean;
  /** Taille max en bytes */
  maxSize?: number;
  /** Texte du bouton */
  label?: string;
  /** Désactivé */
  disabled?: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onUpload,
  accept,
  multiple = false,
  maxSize = 50 * 1024 * 1024, // 50MB
  label = 'Uploader un fichier',
  disabled = false,
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = Array.from(event.target.files || []);

      for (const file of selectedFiles) {
        if (file.size > maxSize) {
          setFiles((prev) => [
            ...prev,
            { file, progress: 0, error: `Fichier trop gros (max ${Math.round(maxSize / 1024 / 1024)}MB)` },
          ]);
          continue;
        }

        const uploadedFile: UploadedFile = { file, progress: 0 };
        setFiles((prev) => [...prev, uploadedFile]);

        try {
          const key = await onUpload(file);
          setFiles((prev) =>
            prev.map((f) =>
              f.file === file ? { ...f, key, progress: 100 } : f
            )
          );
        } catch {
          setFiles((prev) =>
            prev.map((f) =>
              f.file === file ? { ...f, error: 'Erreur d\'upload' } : f
            )
          );
        }
      }

      // Reset input
      if (inputRef.current) inputRef.current.value = '';
    },
    [onUpload, maxSize]
  );

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <Box>
      <input
        type="file"
        ref={inputRef}
        onChange={handleFileSelect}
        accept={accept}
        multiple={multiple}
        style={{ display: 'none' }}
      />

      <Button
        variant="outlined"
        startIcon={<CloudUploadIcon />}
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
      >
        {label}
      </Button>

      {files.length > 0 && (
        <List dense sx={{ mt: 1 }}>
          {files.map((f, index) => (
            <ListItem
              key={index}
              secondaryAction={
                <IconButton edge="end" size="small" onClick={() => removeFile(index)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              }
            >
              <ListItemIcon>
                {f.progress > 0 && f.progress < 100 ? (
                  <CircularProgress size={24} />
                ) : (
                  <InsertDriveFileIcon />
                )}
              </ListItemIcon>
              <ListItemText
                primary={f.file.name}
                secondary={
                  f.error ? (
                    <Typography color="error" variant="caption">{f.error}</Typography>
                  ) : (
                    formatSize(f.file.size)
                  )
                }
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
};
