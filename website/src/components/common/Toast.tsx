import React, {useEffect} from 'react';
import {Snackbar, Alert} from '@mui/material';
import {useAtom} from 'jotai';
import {toastAtom, toastManagerAtom, ToastMessage} from '../../store/toast';

const Toast: React.FC = () => {
    const [toasts] = useAtom(toastAtom);
    const [, dispatchToast] = useAtom(toastManagerAtom);

    const handleClose = (id: string) => {
        dispatchToast({type: 'remove', payload: id});
    };

    return (
        <>
            {toasts.map((toast) => (
                <Snackbar
                    key={toast.id}
                    open={true}
                    autoHideDuration={5000}
                    onClose={() => handleClose(toast.id)}
                >
                    <Alert onClose={() => handleClose(toast.id)} severity={toast.type} sx={{width: '100%'}}>
                        {toast.message}
                    </Alert>
                </Snackbar>
            ))}
        </>
    );
};

export default Toast;