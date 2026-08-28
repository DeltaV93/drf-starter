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
  Divider,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddIcon from '@mui/icons-material/Add';
import OptimizeIcon from '@mui/icons-material/Tune';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import LoadingSpinner from '../common/LoadingSpinner';
import { useRouteOptimization } from '../../hooks/useRouteOptimization';
import { useTrips, type TripHome } from '../../hooks/useTrips';
import { shape, spacingUnit } from '../../styles/brand';
import { validateTripTimes, validateFields } from '../../lib/validation';

interface AddHomeForm {
  address: string;
  start_time: string;
  end_time: string;
}

interface FormErrors {
  address?: string;
  start_time?: string;
  end_time?: string;
}

export default function TripDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { trips, loading: tripsLoading, loadTrips, updateTrip } = useTrips();
  const { optimizeRoute, loading: optimizing } = useRouteOptimization();

  const trip = useMemo(() => trips.find((t) => t.id === parseInt(id || '0')), [trips, id]);
  const [openDialog, setOpenDialog] = useState(false);
  const [addLoading, setAddLoading] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
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
    setFormErrors({});
  };

  const handleSaveHome = async () => {
    // Validate form
    const addressError = validateFields({ address: formData.address }).find((e) => e.field === 'address');
    const timeErrors = validateTripTimes(formData.start_time, formData.end_time);

    const errors: FormErrors = {};
    if (addressError) errors.address = addressError.message;
    timeErrors.forEach((e) => {
      errors[e.field as keyof FormErrors] = e.message;
    });

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

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
      <Box sx={{ py: spacingUnit * 2 }}>
        <Button
          onClick={() => navigate('/trips')}
          sx={{ mb: spacingUnit * 2 }}
          startIcon={<ArrowBackIcon />}
        >
          Back to Trips
        </Button>

        <Box sx={{ mb: spacingUnit * 3, pb: spacingUnit * 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Typography variant="h3" component="h1" gutterBottom>
            {trip.name}
          </Typography>
          <Box sx={{ mt: spacingUnit * 1.5 }}>
            <Typography variant="body2" color="textSecondary" sx={{ mb: spacingUnit }}>
              <strong>From:</strong>
            </Typography>
            <Typography variant="body1" sx={{ mb: spacingUnit * 2, pl: spacingUnit }}>
              {trip.start_address}
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: spacingUnit }}>
              <strong>To:</strong>
            </Typography>
            <Typography variant="body1" sx={{ pl: spacingUnit }}>
              {trip.end_address}
            </Typography>
          </Box>
        </Box>

        <Grid container spacing={spacingUnit}>
          <Grid
            {...({ item: true, xs: 12, md: 6 } as any)}
          >
            <Card sx={{ height: '100%', borderRadius: shape.card }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: spacingUnit * 1.5 }}>
                  <Typography variant="h6">Homes to Visit</Typography>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={handleAddHome}
                    startIcon={<AddIcon />}
                    sx={{ borderRadius: shape.button }}
                  >
                    Add
                  </Button>
                </Box>

                {trip.homes.length === 0 ? (
                  <Box sx={{ py: spacingUnit * 2, textAlign: 'center' }}>
                    <Typography variant="body2" color="textSecondary">
                      No homes added yet.
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Start by adding the first home you want to visit.
                    </Typography>
                  </Box>
                ) : (
                  <List sx={{ p: 0 }}>
                    {trip.homes.map((home, index) => (
                      <Box key={index}>
                        <ListItem sx={{ px: 0, py: spacingUnit * 1.25 }}>
                          <ListItemText
                            primary={
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {index + 1}. {home.address}
                              </Typography>
                            }
                            secondary={
                              <Typography variant="caption" color="textSecondary">
                                {new Date(home.start_time).toLocaleTimeString()} - {new Date(home.end_time).toLocaleTimeString()}
                              </Typography>
                            }
                          />
                        </ListItem>
                        {index < trip.homes.length - 1 && <Divider sx={{ my: 0 }} />}
                      </Box>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid
            {...({ item: true, xs: 12, md: 6 } as any)}
          >
            <Card sx={{ height: '100%', borderRadius: shape.card }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Optimized Route
                </Typography>
                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleOptimizeRoute}
                  disabled={trip.homes.length === 0 || optimizing}
                  startIcon={<OptimizeIcon />}
                  sx={{ mb: spacingUnit * 2, borderRadius: shape.button }}
                >
                  {optimizing ? 'Optimizing...' : 'Optimize Route'}
                </Button>

                {optimizedHomes.length === 0 ? (
                  <Box sx={{ py: spacingUnit * 2, textAlign: 'center' }}>
                    <Typography variant="body2" color="textSecondary">
                      Optimize your route
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      to see the recommended visiting order.
                    </Typography>
                  </Box>
                ) : (
                  <List sx={{ p: 0 }}>
                    {optimizedHomes.map((home, index) => (
                      <Box key={index}>
                        <ListItem sx={{ px: 0, py: spacingUnit * 1.25 }}>
                          <ListItemText
                            primary={
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                Stop {index + 1}: {home.address}
                              </Typography>
                            }
                            secondary={
                              <Typography variant="caption" color="textSecondary">
                                {new Date(home.start_time).toLocaleTimeString()} - {new Date(home.end_time).toLocaleTimeString()}
                              </Typography>
                            }
                          />
                        </ListItem>
                        {index < optimizedHomes.length - 1 && <Divider sx={{ my: 0 }} />}
                      </Box>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
        slotProps={{ paper: { sx: { borderRadius: shape.card } } }}
      >
        <DialogTitle sx={{ fontWeight: 600 }}>Add Home to Visit</DialogTitle>
        <DialogContent sx={{ pt: spacingUnit * 2 }}>
          <TextField
            fullWidth
            label="Address"
            value={formData.address}
            onChange={(e) => {
              setFormData({ ...formData, address: e.target.value });
              if (formErrors.address) setFormErrors({ ...formErrors, address: undefined });
            }}
            margin="normal"
            placeholder="e.g., 123 Oak St, City, State"
            variant="outlined"
            size="small"
            error={!!formErrors.address}
            helperText={formErrors.address ?? ''}
          />
          <TextField
            fullWidth
            label="Start Time"
            type="datetime-local"
            value={formData.start_time}
            onChange={(e) => {
              setFormData({ ...formData, start_time: e.target.value });
              if (formErrors.start_time) setFormErrors({ ...formErrors, start_time: undefined });
            }}
            margin="normal"
            slotProps={{ inputLabel: { shrink: true } }}
            variant="outlined"
            size="small"
            error={!!formErrors.start_time}
            helperText={formErrors.start_time ?? ''}
          />
          <TextField
            fullWidth
            label="End Time"
            type="datetime-local"
            value={formData.end_time}
            onChange={(e) => {
              setFormData({ ...formData, end_time: e.target.value });
              if (formErrors.end_time) setFormErrors({ ...formErrors, end_time: undefined });
            }}
            margin="normal"
            slotProps={{ inputLabel: { shrink: true } }}
            variant="outlined"
            size="small"
            error={!!formErrors.end_time}
            helperText={formErrors.end_time ?? ''}
          />
        </DialogContent>
        <DialogActions sx={{ p: spacingUnit * 1.5 }}>
          <Button onClick={handleCloseDialog} disabled={addLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleSaveHome}
            variant="contained"
            disabled={addLoading}
            sx={{ borderRadius: shape.button }}
          >
            {addLoading ? 'Adding...' : 'Add Home'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
