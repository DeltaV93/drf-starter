import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  TextField,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import LoadingSpinner from '../common/LoadingSpinner';
import { useTrips, type Trip } from '../../hooks/useTrips';
import { shape, spacingUnit } from '../../styles/brand';
import { validateFields } from '../../lib/validation';

export default function TripsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { trips, loading, loadTrips, createTrip } = useTrips();
  const [openDialog, setOpenDialog] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [formData, setFormData] = useState({
    name: '',
    start_address: '',
    end_address: '',
  });

  useEffect(() => {
    loadTrips();
  }, [loadTrips]);

  const handleOpenDialog = () => setOpenDialog(true);
  const handleCloseDialog = () => {
    setOpenDialog(false);
    setFormData({ name: '', start_address: '', end_address: '' });
    setFormErrors({});
  };

  const handleCreateTrip = async () => {
    // Validate form
    const errors = validateFields({
      tripName: formData.name,
      address: formData.start_address,
    });

    const errorMap: Record<string, string> = {};
    errors.forEach((e) => {
      if (e.field === 'tripName') {
        errorMap.name = e.message;
      } else if (e.field === 'address') {
        errorMap.start_address = e.message;
      }
    });

    const endAddressError = validateFields({ address: formData.end_address }).find((e) => e.field === 'address');
    if (endAddressError) {
      errorMap.end_address = endAddressError.message;
    }

    if (Object.keys(errorMap).length > 0) {
      setFormErrors(errorMap);
      return;
    }

    setCreateLoading(true);
    try {
      await createTrip({
        ...formData,
        homes: [],
      });
      handleCloseDialog();
      setFormData({ name: '', start_address: '', end_address: '' });
    } catch (error) {
      console.error('Failed to create trip:', error);
    } finally {
      setCreateLoading(false);
    }
  };

  const handleTripClick = (trip: Trip) => {
    navigate(`/trips/${trip.id}`);
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
              {t('trips', 'Trips')}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Plan and optimize your home-hunting route
            </Typography>
          </Box>
          <Button
            variant="contained"
            onClick={handleOpenDialog}
            startIcon={<AddIcon />}
            sx={{ borderRadius: shape.button }}
          >
            {t('newTrip', 'New Trip')}
          </Button>
        </Box>

        {trips.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: spacingUnit * 4 }}>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              {t('noTrips', 'No trips yet.')}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Create your first trip to start planning your route
            </Typography>
          </Box>
        ) : (
          <Grid container spacing={spacingUnit}>
            {trips.map((trip) => (
              <Grid item xs={12} sm={6} md={4} key={trip.id}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    cursor: 'pointer',
                    borderRadius: shape.card,
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: '0 12px 20px rgba(0, 0, 0, 0.15)',
                    },
                  }}
                  onClick={() => handleTripClick(trip)}
                >
                  <CardContent sx={{ flexGrow: 1, pb: spacingUnit }}>
                    <Typography gutterBottom variant="h6" component="div">
                      {trip.name}
                    </Typography>
                    <Box sx={{ mt: spacingUnit, mb: spacingUnit }}>
                      <Typography variant="caption" sx={{ display: 'block', mb: spacingUnit * 0.5 }}>
                        <strong>From:</strong>
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ mb: spacingUnit }}>
                        {trip.start_address}
                      </Typography>
                      <Typography variant="caption" sx={{ display: 'block', mb: spacingUnit * 0.5 }}>
                        <strong>To:</strong>
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        {trip.end_address}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        mt: spacingUnit,
                        pt: spacingUnit,
                        borderTop: '1px solid',
                        borderColor: 'divider',
                      }}
                    >
                      <Typography variant="caption" color="textSecondary">
                        {trip.homes.length} {trip.homes.length === 1 ? 'home' : 'homes'} in this trip
                      </Typography>
                    </Box>
                  </CardContent>
                  <CardActions sx={{ pt: 0 }}>
                    <Button size="small" color="primary">
                      View Details →
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>

      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { borderRadius: shape.card } }}
      >
        <DialogTitle sx={{ fontWeight: 600 }}>
          {t('createNewTrip', 'Create New Trip')}
        </DialogTitle>
        <DialogContent sx={{ pt: spacingUnit * 2 }}>
          <TextField
            fullWidth
            label={t('tripName', 'Trip Name')}
            value={formData.name}
            onChange={(e) => {
              setFormData({ ...formData, name: e.target.value });
              if (formErrors.name) setFormErrors({ ...formErrors, name: undefined });
            }}
            margin="normal"
            placeholder="e.g., Downtown Open Houses"
            variant="outlined"
            size="small"
            error={!!formErrors.name}
            helperText={formErrors.name}
          />
          <TextField
            fullWidth
            label={t('startAddress', 'Starting Address')}
            value={formData.start_address}
            onChange={(e) => {
              setFormData({ ...formData, start_address: e.target.value });
              if (formErrors.start_address) setFormErrors({ ...formErrors, start_address: undefined });
            }}
            margin="normal"
            placeholder="e.g., 123 Main St, City, State"
            variant="outlined"
            size="small"
            error={!!formErrors.start_address}
            helperText={formErrors.start_address}
          />
          <TextField
            fullWidth
            label={t('endAddress', 'Ending Address')}
            value={formData.end_address}
            onChange={(e) => {
              setFormData({ ...formData, end_address: e.target.value });
              if (formErrors.end_address) setFormErrors({ ...formErrors, end_address: undefined });
            }}
            margin="normal"
            placeholder="e.g., 456 Oak Ave, City, State"
            variant="outlined"
            size="small"
            error={!!formErrors.end_address}
            helperText={formErrors.end_address}
          />
        </DialogContent>
        <DialogActions sx={{ p: spacingUnit * 1.5 }}>
          <Button onClick={handleCloseDialog} disabled={createLoading}>
            {t('cancel', 'Cancel')}
          </Button>
          <Button
            onClick={handleCreateTrip}
            variant="contained"
            disabled={createLoading}
            sx={{ borderRadius: shape.button }}
          >
            {createLoading ? 'Creating...' : t('create', 'Create')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
