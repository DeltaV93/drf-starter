import React, {useState} from 'react';
import {Box, Button, Grid, InputAdornment, TextField, Typography} from '@mui/material';
import {useTranslation} from 'react-i18next';
import {CardCvcElement, CardExpiryElement, CardNumberElement, useElements, useStripe} from '@stripe/react-stripe-js';

// import CreditCardIcon from '@mui/icons-material/CreditCard';

interface PaymentFormProps {
    amount: number;
    onPaymentSubmit: (paymentMethod: any) => void;
}

const StripeInput = ({component: Component, ...props}) => {
    return (
        <Component
            options={{
                style: {
                    base: {
                        fontSize: '16px',
                        color: '#424770',
                        '::placeholder': {
                            color: '#aab7c4',
                        },
                    },
                    invalid: {
                        color: '#9e2146',
                    },
                },
            }}
            {...props}
        />
    );
};

const PaymentForm: React.FC<PaymentFormProps> = ({amount, onPaymentSubmit}) => {
    const {t} = useTranslation();
    const stripe = useStripe();
    const elements = useElements();
    const [discountCode, setDiscountCode] = useState('');
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!stripe || !elements) return;

        const cardElement = elements.getElement(CardNumberElement);
        if (!cardElement) return;

        const {error, paymentMethod} = await stripe.createPaymentMethod({
            type: 'card',
            card: cardElement,
        });

        if (error) {
            setError(error.message || 'An error occurred');
        } else {
            onPaymentSubmit({paymentMethod, discountCode});
        }
    };

    return (
        <Box component="form" onSubmit={handleSubmit} sx={{width: '100%', maxWidth: 500}}>
            <Typography variant="h5" gutterBottom fontWeight="bold">
                {t('finalStepPayment')}
            </Typography>
            <Typography variant="body1" gutterBottom color="text.secondary">
                {t('completePayment')}
            </Typography>

            <Box sx={{mb: 3, mt: 3}}>
                <Typography variant="subtitle1" gutterBottom>
                    {t('cardNumber')}
                </Typography>
                <TextField
                    fullWidth
                    InputProps={{
                        inputComponent: StripeInput,
                        inputProps: {
                            component: CardNumberElement,
                        },
                        startAdornment: (
                            <InputAdornment position="start">
                                {/*<CreditCardIcon />*/}
                            </InputAdornment>
                        ),
                    }}
                    sx={{mb: 2}}
                />
            </Box>

            <Grid container spacing={2} sx={{mb: 3}}>
                <Grid item xs={6}>
                    <TextField
                        fullWidth
                        label={t('expiry')}
                        InputProps={{
                            inputComponent: StripeInput,
                            inputProps: {
                                component: CardExpiryElement,
                            },
                        }}
                    />
                </Grid>
                <Grid item xs={6}>
                    <TextField
                        fullWidth
                        label={t('cvc')}
                        InputProps={{
                            inputComponent: StripeInput,
                            inputProps: {
                                component: CardCvcElement,
                            },
                        }}
                    />
                </Grid>
            </Grid>

            <TextField
                fullWidth
                label={t('discountCode')}
                value={discountCode}
                onChange={(e) => setDiscountCode(e.target.value)}
                sx={{mb: 3}}
                InputProps={{
                    endAdornment: (
                        <InputAdornment position="end">
                            <Button color="primary">{t('apply')}</Button>
                        </InputAdornment>
                    ),
                }}
            />

            {error && (
                <Typography color="error" sx={{mb: 2}}>
                    {error}
                </Typography>
            )}

            <Button
                type="submit"
                variant="contained"
                color="primary"
                fullWidth
                size="large"
                disabled={!stripe}
                sx={{
                    mt: 2,
                    py: 1.5,
                    backgroundColor: '#1565c0',
                    '&:hover': {
                        backgroundColor: '#0d47a1',
                    }
                }}
            >
                {t('payNow')} ${amount.toFixed(2)}
            </Button>
        </Box>
    );
};

export default PaymentForm;