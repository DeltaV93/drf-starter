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
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Select,
  TextField,
  Typography,
  IconButton,
  Divider,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { shape, spacingUnit } from '../../styles/brand';

interface Document {
  id: number;
  filename: string;
  category: string;
  created_at: string;
  file_size: number;
}

export default function DocumentsPage() {
  const { t } = useTranslation();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [formData, setFormData] = useState({
    filename: '',
    category: 'other',
  });

  const handleOpenDialog = () => setOpenDialog(true);
  const handleCloseDialog = () => {
    setOpenDialog(false);
    setFormData({ filename: '', category: 'other' });
  };

  const handleUploadDocument = async () => {
    if (!formData.filename) return;
    setUploading(true);
    // TODO: Implement API call to upload document
    setUploading(false);
    handleCloseDialog();
  };

  const handleDeleteDocument = async (id: number) => {
    // TODO: Implement API call to delete document
    setDocuments(documents.filter((doc) => doc.id !== id));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const categories = [
    { value: 'receipts', label: 'Receipts' },
    { value: 'mortgage', label: 'Mortgage' },
    { value: 'offer_letter', label: 'Offer Letter' },
    { value: 'inspection', label: 'Inspection' },
    { value: 'appraisal', label: 'Appraisal' },
    { value: 'title', label: 'Title' },
    { value: 'other', label: 'Other' },
  ];

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
              {t('documents', 'Documents')}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Securely store and organize your home-related documents
            </Typography>
          </Box>
          <Button
            variant="contained"
            onClick={handleOpenDialog}
            startIcon={<CloudUploadIcon />}
            sx={{ borderRadius: shape.button }}
          >
            {t('uploadDocument', 'Upload')}
          </Button>
        </Box>

        {documents.length === 0 ? (
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
              <CloudUploadIcon sx={{ fontSize: 40, color: 'primary.main' }} />
            </Box>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              {t('noDocuments', 'No documents yet.')}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Upload documents to keep them organized in one secure place
            </Typography>
          </Box>
        ) : (
          <Card sx={{ borderRadius: shape.card }}>
            <CardContent sx={{ p: 0 }}>
              <List sx={{ p: 0 }}>
                {documents.map((doc, index) => (
                  <Box key={doc.id}>
                    <ListItem
                      sx={{
                        px: spacingUnit * 2,
                        py: spacingUnit * 1.5,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <ListItemText
                        primary={
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {doc.filename}
                          </Typography>
                        }
                        secondary={
                          <Box sx={{ mt: spacingUnit * 0.5 }}>
                            <Typography variant="caption" color="textSecondary">
                              {categories.find((c) => c.value === doc.category)?.label} •{' '}
                              {formatFileSize(doc.file_size)} • {new Date(doc.created_at).toLocaleDateString()}
                            </Typography>
                          </Box>
                        }
                      />
                      <Box sx={{ display: 'flex', gap: spacingUnit * 0.5 }}>
                        <IconButton size="small" title="Download document">
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteDocument(doc.id)}
                          title="Delete document"
                          color="error"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    </ListItem>
                    {index < documents.length - 1 && <Divider sx={{ my: 0 }} />}
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
        <DialogTitle sx={{ fontWeight: 600 }}>{t('uploadDocument', 'Upload Document')}</DialogTitle>
        <DialogContent sx={{ pt: spacingUnit * 2 }}>
          <TextField
            fullWidth
            label="File Name"
            value={formData.filename}
            onChange={(e) => setFormData({ ...formData, filename: e.target.value })}
            margin="normal"
            placeholder="e.g., home_inspection.pdf"
            variant="outlined"
            size="small"
          />
          <FormControl fullWidth margin="normal" size="small">
            <InputLabel>Category</InputLabel>
            <Select
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              label="Category"
            >
              {categories.map((cat) => (
                <MenuItem key={cat.value} value={cat.value}>
                  {cat.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ p: spacingUnit * 1.5 }}>
          <Button onClick={handleCloseDialog} disabled={uploading}>
            Cancel
          </Button>
          <Button
            onClick={handleUploadDocument}
            variant="contained"
            disabled={uploading || !formData.filename}
            sx={{ borderRadius: shape.button }}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
