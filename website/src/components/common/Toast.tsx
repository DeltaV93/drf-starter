import { Alert, Snackbar } from '@mui/material';

import { useToast, useToasts } from '../../store/toast';

/**
 * Renders queued toasts. Only the oldest is shown at a time -- stacking
 * MUI Snackbars puts them all in the same corner, on top of each other.
 */
export default function Toast() {
  const toasts = useToasts();
  const { dismiss } = useToast();
  const current = toasts[0];

  if (!current) return null;

  return (
    <Snackbar
      key={current.id}
      open
      autoHideDuration={current.duration}
      onClose={(_event, reason) => {
        if (reason !== 'clickaway') dismiss(current.id);
      }}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
    >
      <Alert
        severity={current.severity}
        variant="filled"
        onClose={() => dismiss(current.id)}
        sx={{ width: '100%' }}
      >
        {current.message}
      </Alert>
    </Snackbar>
  );
}
