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
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Switch,
  TextField,
  Typography,
  Divider,
  Chip,
  Tooltip,
} from '@mui/material';
import LinkIcon from '@mui/icons-material/Link';
import DeleteIcon from '@mui/icons-material/Delete';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { shape, spacingUnit } from '../../styles/brand';

interface ShareLink {
  id: number;
  token: string;
  expires_at: string | null;
  created_at: string;
  document_count: number;
  has_password: boolean;
}

export default function SharesPage() {
  const { t } = useTranslation();
  const [shares, setShares] = useState<ShareLink[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({
    documents: [] as number[],
    password: '',
    expires_in_days: '',
  });

  const handleOpenDialog = () => setOpenDialog(true);
  const handleCloseDialog = () => {
    setOpenDialog(false);
    setFormData({ documents: [], password: '', expires_in_days: '' });
  };

  const handleCreateShare = async () => {
    setCreating(true);
    // TODO: Implement API call to create share link
    setCreating(false);
    handleCloseDialog();
  };

  const handleDeleteShare = async (id: number) => {
    // TODO: Implement API call to delete share link
    setShares(shares.filter((share) => share.id !== id));
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
                              {share.has_password && (
                                <Chip label="Password Protected" size="small" color="primary" variant="outlined" />
                              )}
                              {isLinkExpired(share.expires_at) && (
                                <Chip label="Expired" size="small" color="error" variant="outlined" />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box sx={{ mt: spacingUnit * 0.5 }}>
                              <Typography variant="caption" color="textSecondary" sx={{ display: 'block' }}>
                                {share.document_count} document{share.document_count !== 1 ? 's' : ''} • Created{' '}
                                {new Date(share.created_at).toLocaleDateString()}
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
        PaperProps={{ sx: { borderRadius: shape.card } }}
      >
        <DialogTitle sx={{ fontWeight: 600 }}>{t('createShare', 'Create Share Link')}</DialogTitle>
        <DialogContent sx={{ pt: spacingUnit * 2 }}>
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
          />
          <FormControlLabel
            control={<Switch />}
            label="Allow recipients to download"
            sx={{ mt: spacingUnit }}
          />
        </DialogContent>
        <DialogActions sx={{ p: spacingUnit * 1.5 }}>
          <Button onClick={handleCloseDialog} disabled={creating}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateShare}
            variant="contained"
            disabled={creating}
            sx={{ borderRadius: shape.button }}
          >
            {creating ? 'Creating...' : 'Create Link'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
