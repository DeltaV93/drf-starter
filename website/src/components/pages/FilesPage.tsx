/**
 * Uploading and managing files.
 *
 * Only mounted when VITE_UPLOADS_ENABLED matches the backend's
 * UPLOADS_ENABLED -- see App.tsx.
 */

import {
  Box,
  Button,
  CircularProgress,
  Container,
  List,
  ListItem,
  ListItemText,
  Paper,
  Typography,
} from '@mui/material';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { apiCall, apiData, http } from '../../lib/api';
import { routes } from '../../lib/routes';
import type { Attachment } from '../../lib/types';
import { useToast } from '../../store/toast';

function humanSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FilesPage() {
  const { t } = useTranslation();
  const toast = useToast();

  const [files, setFiles] = useState<Attachment[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchFiles = useCallback(
    () => apiData<Attachment[]>({ url: routes.api.files.list() }),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await fetchFiles();
        if (!cancelled) setFiles(next ?? []);
      } catch (error) {
        if (!cancelled) toast.error(error instanceof Error ? error.message : t('genericError'));
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchFiles, toast, t]);

  const upload = async (file: File) => {
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      // Multipart, so the browser sets its own boundary -- api.ts still adds
      // the CSRF header.
      await http.post(routes.api.files.list(), body);
      setFiles((await fetchFiles()) ?? []);
      toast.success(t('fileUploaded'));
    } catch (error) {
      // The backend refuses anything whose sniffed type is not allowed, and
      // says what the file actually is.
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        (error instanceof Error ? error.message : t('genericError'));
      toast.error(message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const remove = async (file: Attachment) => {
    try {
      await apiCall({ method: 'delete', url: routes.api.files.detail(file.id) });
      setFiles((await fetchFiles()) ?? []);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  if (!loaded) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Typography variant="h4" gutterBottom>
        {t('files')}
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <input
          ref={inputRef}
          type="file"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void upload(file);
          }}
        />
        <Button
          variant="contained"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? t('uploading') : t('chooseFile')}
        </Button>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {t('uploadHelp')}
        </Typography>
      </Paper>

      <Paper sx={{ p: 3 }}>
        {files.length === 0 ? (
          <Typography color="text.secondary">{t('noFiles')}</Typography>
        ) : (
          <List dense>
            {files.map((file) => (
              <ListItem
                key={file.id}
                secondaryAction={
                  <>
                    {/* Goes through the download view, which checks who is
                        asking before issuing a URL that expires. */}
                    <Button size="small" href={file.download_url}>
                      {t('download')}
                    </Button>
                    <Button size="small" color="error" onClick={() => void remove(file)}>
                      {t('delete')}
                    </Button>
                  </>
                }
              >
                <ListItemText
                  primary={file.original_name || `#${file.id}`}
                  secondary={`${file.content_type} · ${humanSize(file.size_bytes)}`}
                />
              </ListItem>
            ))}
          </List>
        )}
      </Paper>
    </Container>
  );
}
