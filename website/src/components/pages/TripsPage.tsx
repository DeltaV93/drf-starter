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
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import LoadingSpinner from '../common/LoadingSpinner';
import { useTrips, type Trip } from '../../hooks/useTrips';

export default function TripsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { trips, loading, createTrip } = useTrips();
  const [openDialog, setOpenDialog] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    start_address: '',
    end_address: '',
  });

  useEffect(() => {
    // Load trips on component mount
  }, []);

  const handleOpenDialog = () => setOpenDialog(true);
  const handleCloseDialog = () => {
    setOpenDialog(false);
    setFormData({ name: '', start_address: '', end_address: '' });
  };

  const handleCreateTrip = async () => {
    if (!formData.name || !formData.start_address || !formData.end_address) {
      return;
    }

    try {
      await createTrip({
        ...formData,
        homes: [],
      });
      handleCloseDialog();
    } catch (error) {
      console.error('Failed to create trip:', error);
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
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Typography variant="h3" component="h1">
            {t('trips', 'Trips')}
          </Typography>
          <Button variant="contained" onClick={handleOpenDialog}>
            {t('newTrip', 'New Trip')}
          </Button>
        </Box>

        {trips.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="body1" color="textSecondary" gutterBottom>
              {t('noTrips', 'No trips yet. Create one to get started!')}
            </Typography>
          </Box>
        ) : (
          <Grid container spacing={3}>
            {trips.map((trip) => (
              <Grid item xs={12} sm={6} md={4} key={trip.id}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    cursor: 'pointer',
                    '&:hover': { boxShadow: 6 },
                  }}
                  onClick={() => handleTripClick(trip)}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Typography gutterBottom variant="h6" component="div">
                      {trip.name}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" gutterBottom>
                      <strong>From:</strong> {trip.start_address}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      <strong>To:</strong> {trip.end_address}
                    </Typography>
                    <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 1 }}>
                      {trip.homes.length} {trip.homes.length === 1 ? 'home' : 'homes'}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button size="small">View Details</Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{t('createNewTrip', 'Create New Trip')}</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <TextField
            fullWidth
            label={t('tripName', 'Trip Name')}
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
            placeholder="e.g., Downtown Open Houses"
          />
          <TextField
            fullWidth
            label={t('startAddress', 'Starting Address')}
            value={formData.start_address}
            onChange={(e) => setFormData({ ...formData, start_address: e.target.value })}
            margin="normal"
            placeholder="e.g., 123 Main St, City, State"
          />
          <TextField
            fullWidth
            label={t('endAddress', 'Ending Address')}
            value={formData.end_address}
            onChange={(e) => setFormData({ ...formData, end_address: e.target.value })}
            margin="normal"
            placeholder="e.g., 456 Oak Ave, City, State"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>{t('cancel', 'Cancel')}</Button>
          <Button onClick={handleCreateTrip} variant="contained">
            {t('create', 'Create')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
