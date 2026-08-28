import { Box, Button, Container, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';

export default function DocumentsPage() {
  const { t } = useTranslation();

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Typography variant="h3" component="h1">
            {t('documents', 'Documents')}
          </Typography>
          <Button variant="contained">{t('uploadDocument', 'Upload Document')}</Button>
        </Box>

        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="body1" color="textSecondary" gutterBottom>
            {t('noDocuments', 'No documents yet. Upload one to get started!')}
          </Typography>
        </Box>
      </Box>
    </Container>
  );
}
