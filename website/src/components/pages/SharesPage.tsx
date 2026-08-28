import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  List,
  ListItem,
  ListItemText,
  TextField,
  Typography,
  Divider,
  Chip,
  Tooltip,
  Alert,
} from '@mui/material';
import LinkIcon from '@mui/icons-material/Link';
import DeleteIcon from '@mui/icons-material/Delete';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { shape, spacingUnit } from '../../styles/brand';
import { useShares } from '../../hooks/useShares';
import LoadingSpinner from '../common/LoadingSpinner';

export default function SharesPage() {
  const { t } = useTranslation();
  const { shares, loading, loadShares, createShare, deleteShare } = useShares();
  const [openDialog, setOpenDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    documents: [] as number[],
    password: '',
    expires_in_days: '',
  });

  useEffect(() => {
    loadShares();
  }, [loadShares]);

  const handleOpenDialog = () => setOpenDialog(true);
  const handleCloseDialog = () => {
    setOpenDialog(false);
    setFormData({ documents: [], password: '', expires_in_days: '' });
    setError(null);
  };

  const handleCreateShare = async () => {
    if (formData.documents.length === 0) {
      setError('Please select at least one document to share');
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const expiresAt = formData.expires_in_days
        ? new Date(Date.now() + parseInt(formData.expires_in_days) * 24 * 60 * 60 * 1000).toISOString()
        : undefined;
      await createShare({
        document_ids: formData.documents,
        password: formData.password || undefined,
        expires_at: expiresAt,
      });
      handleCloseDialog();
    } catch (err) {
      setError('Failed to create share link. Please try again.');
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteShare = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this share link?')) {
      try {
        await deleteShare(id);
      } catch (err) {
        setError('Failed to delete share link');
        console.error(err);
      }
    }
  };

  const handleCopyLink = (token: string) => {
    const url = `${window.location.origin}/share/${token}`;
    navigator.clipboard.writeText(url);
  };

  const isLinkExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  const getExpirationText = (expiresAt: string | null) => {
    if (!expiresAt) return 'Never expires';
    const date = new Date(expiresAt);
    if (isLinkExpired(expiresAt)) return 'Expired';
    const days = Math.ceil((date.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
    if (days === 0) return 'Expires today';
    if (days === 1) return 'Expires tomorrow';
    return `Expires in ${days} days`;
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: spacingUnit * 2 }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: spacingUnit * 2,
            gap: spacingUnit,
            flexWrap: 'wrap',
          }}
        >
          <Box>
            <Typography variant="h3" component="h1" sx={{ mb: spacingUnit * 0.5 }}>
              {t('shares', 'Shared Documents')}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Share documents securely with password protection and expiration
            </Typography>
          </Box>
          <Button
            variant="contained"
            onClick={handleOpenDialog}
            startIcon={<LinkIcon />}
            sx={{ borderRadius: shape.button }}
          >
            {t('createShare', 'Create Share Link')}
          </Button>
        </Box>

        {error && (
          <Alert
            severity="error"
            onClose={() => setError(null)}
            sx={{ mb: spacingUnit * 2 }}
          >
            {error}
          </Alert>
        )}

        {shares.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: spacingUnit * 4 }}>
            <Box
              sx={{
                width: 80,
                height: 80,
                margin: '0 auto',
                mb: spacingUnit * 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: 'action.hover',
                borderRadius: '50%',
              }}
            >
              <LinkIcon sx={{ fontSize: 40, color: 'primary.main' }} />
            </Box>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              {t('noShares', 'No shared links yet.')}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Create a share link to securely share documents with others
            </Typography>
          </Box>
        ) : (
          <Card sx={{ borderRadius: shape.card }}>
            <CardContent sx={{ p: 0 }}>
              <List sx={{ p: 0 }}>
                {shares.map((share, index) => (
                  <Box key={share.id}>
                    <ListItem
                      sx={{
                        px: spacingUnit * 2,
                        py: spacingUnit * 1.5,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                      }}
                    >
                      <Box sx={{ flex: 1 }}>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', gap: spacingUnit, alignItems: 'center', flexWrap: 'wrap' }}>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                Share Link
                              </Typography>
                              {isLinkExpired(share.expires_at) && (
                                <Chip label="Expired" size="small" color="error" variant="outlined" />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box sx={{ mt: spacingUnit * 0.5 }}>
                              <Typography variant="caption" color="textSecondary" sx={{ display: 'block' }}>
                                Created {new Date(share.created_at).toLocaleDateString()}
                              </Typography>
                              <Typography variant="caption" color="textSecondary" sx={{ display: 'block' }}>
                                {getExpirationText(share.expires_at)}
                              </Typography>
                            </Box>
                          }
                        />
                      </Box>
                      <Box sx={{ display: 'flex', gap: spacingUnit * 0.5 }}>
                        <Tooltip title="Copy link">
                          <IconButton size="small" onClick={() => handleCopyLink(share.token)}>
                            <ContentCopyIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete share">
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteShare(share.id)}
                            color="error"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </ListItem>
                    {index < shares.length - 1 && <Divider sx={{ my: 0 }} />}
                  </Box>
                ))}
              </List>
            </CardContent>
          </Card>
        )}
      </Box>

      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
        slotProps={{ paper: { sx: { borderRadius: shape.card } } }}
      >
        <DialogTitle sx={{ fontWeight: 600 }}>{t('createShare', 'Create Share Link')}</DialogTitle>
        <DialogContent sx={{ pt: spacingUnit * 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: spacingUnit }}>
              {error}
            </Alert>
          )}
          <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: spacingUnit }}>
            Configure the share settings below
          </Typography>
          <TextField
            fullWidth
            label="Password (Optional)"
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            margin="normal"
            placeholder="Leave blank for no password"
            variant="outlined"
            size="small"
          />
          <TextField
            fullWidth
            label="Expires in (Days)"
            type="number"
            value={formData.expires_in_days}
            onChange={(e) => setFormData({ ...formData, expires_in_days: e.target.value })}
            margin="normal"
            placeholder="Leave blank to never expire"
            variant="outlined"
            size="small"
            inputProps={{ min: 1 }}
          />
        </DialogContent>
        <DialogActions sx={{ p: spacingUnit * 1.5 }}>
          <Button onClick={handleCloseDialog} disabled={creating}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateShare}
            variant="contained"
            disabled={creating || formData.documents.length === 0}
            sx={{ borderRadius: shape.button }}
          >
            {creating ? 'Creating...' : 'Create Link'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
