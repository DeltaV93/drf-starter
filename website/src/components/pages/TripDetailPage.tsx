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
  Grid,
  List,
  ListItem,
  ListItemText,
  TextField,
  Typography,
} from '@mui/material';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import LoadingSpinner from '../common/LoadingSpinner';
import { useRouteOptimization } from '../../hooks/useRouteOptimization';
import { useTrips, type TripHome } from '../../hooks/useTrips';

interface AddHomeForm {
  address: string;
  start_time: string;
  end_time: string;
}

export default function TripDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { trips, loading: tripsLoading, loadTrips, updateTrip } = useTrips();
  const { optimizeRoute, loading: optimizing } = useRouteOptimization();

  const trip = useMemo(() => trips.find((t) => t.id === parseInt(id || '0')), [trips, id]);
  const [openDialog, setOpenDialog] = useState(false);
  const [addLoading, setAddLoading] = useState(false);
  const [formData, setFormData] = useState<AddHomeForm>({
    address: '',
    start_time: '',
    end_time: '',
  });
  const [optimizedHomes, setOptimizedHomes] = useState<TripHome[]>(trip?.homes || []);

  // Load trips on mount if not already loaded
  useEffect(() => {
    if (trips.length === 0) {
      loadTrips();
    }
  }, [trips.length, loadTrips]);

  if (!trip) {
    if (tripsLoading) {
      return <LoadingSpinner />;
    }
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="error">
            Trip not found
          </Typography>
          <Button onClick={() => navigate('/trips')} sx={{ mt: 2 }}>
            Back to Trips
          </Button>
        </Box>
      </Container>
    );
  }

  const handleAddHome = () => {
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setFormData({ address: '', start_time: '', end_time: '' });
  };

  const handleSaveHome = async () => {
    if (!formData.address || !formData.start_time || !formData.end_time || !trip) {
      return;
    }

    setAddLoading(true);
    try {
      const newHome: Omit<TripHome, 'id' | 'created_at' | 'visit_order'> = {
        address: formData.address,
        start_time: formData.start_time,
        end_time: formData.end_time,
        lat: 0,
        lng: 0,
      };

      const updatedHomes = [...trip.homes, newHome as TripHome];
      const updatedTrip = await updateTrip(trip.id, {
        name: trip.name,
        start_address: trip.start_address,
        end_address: trip.end_address,
        homes: updatedHomes,
      });

      if (updatedTrip) {
        setOptimizedHomes(updatedTrip.homes);
      }
      handleCloseDialog();
      setFormData({ address: '', start_time: '', end_time: '' });
    } catch (error) {
      console.error('Failed to add home:', error);
    } finally {
      setAddLoading(false);
    }
  };

  const handleOptimizeRoute = async () => {
    if (!trip || trip.homes.length === 0) {
      return;
    }

    try {
      const result = await optimizeRoute(
        trip.homes.map(({ address, start_time, end_time, lat, lng }) => ({
          address,
          start_time,
          end_time,
          lat,
          lng,
        }))
      );

      if (result?.schedule) {
        setOptimizedHomes(result.schedule);
      }
    } catch (error) {
      console.error('Failed to optimize route:', error);
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Button onClick={() => navigate('/trips')} sx={{ mb: 2 }}>
          ← Back to Trips
        </Button>

        <Box sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom>
            {trip.name}
          </Typography>
          <Typography variant="body1" color="textSecondary" gutterBottom>
            <strong>From:</strong> {trip.start_address}
          </Typography>
          <Typography variant="body1" color="textSecondary" gutterBottom>
            <strong>To:</strong> {trip.end_address}
          </Typography>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">Homes to Visit</Typography>
                  <Button size="small" variant="contained" onClick={handleAddHome}>
                    Add Home
                  </Button>
                </Box>

                {trip.homes.length === 0 ? (
                  <Typography variant="body2" color="textSecondary">
                    No homes added yet. Add some to get started.
                  </Typography>
                ) : (
                  <List>
                    {trip.homes.map((home, index) => (
                      <ListItem key={index}>
                        <ListItemText
                          primary={`${index + 1}. ${home.address}`}
                          secondary={`${home.start_time} - ${home.end_time}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Optimized Route
                </Typography>
                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleOptimizeRoute}
                  disabled={trip.homes.length === 0 || optimizing}
                  sx={{ mb: 2 }}
                >
                  {optimizing ? 'Optimizing...' : 'Optimize Route'}
                </Button>

                {optimizedHomes.length === 0 ? (
                  <Typography variant="body2" color="textSecondary">
                    Optimize your route to see the recommended order.
                  </Typography>
                ) : (
                  <List>
                    {optimizedHomes.map((home, index) => (
                      <ListItem key={index}>
                        <ListItemText
                          primary={`Stop ${index + 1}: ${home.address}`}
                          secondary={`${home.start_time} - ${home.end_time}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add Home to Visit</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <TextField
            fullWidth
            label="Address"
            value={formData.address}
            onChange={(e) => setFormData({ ...formData, address: e.target.value })}
            margin="normal"
            placeholder="e.g., 123 Oak St, City, State"
          />
          <TextField
            fullWidth
            label="Start Time"
            type="datetime-local"
            value={formData.start_time}
            onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
            margin="normal"
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            fullWidth
            label="End Time"
            type="datetime-local"
            value={formData.end_time}
            onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
            margin="normal"
            InputLabelProps={{ shrink: true }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} disabled={addLoading}>
            Cancel
          </Button>
          <Button onClick={handleSaveHome} variant="contained" disabled={addLoading}>
            {addLoading ? 'Adding...' : 'Add Home'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
