import {CardElement, useElements, useStripe} from "@stripe/react-stripe-js";
import {useTranslation} from "react-i18next";
import React, {useState} from "react";
import {apiCall} from "../../utils/api.tsx";
import {routes} from "../../libs/routes.ts";
import {Button, Typography} from "@mui/material";

const CheckoutForm = ({selectedPlan, onSuccess}) => {
    const stripe = useStripe();
    const elements = useElements();
    const {t} = useTranslation();
    const [isProcessing, setIsProcessing] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');

    const handleSubmit = async (event) => {
        event.preventDefault();
        console.log(selectedPlan, 'heyeyeyeye')

        if (!stripe || !elements) {
            return;
        }

        setIsProcessing(true);

        try {
            // Create payment method
            const {error, paymentMethod} = await stripe.createPaymentMethod({
                type: 'card',
                card: elements.getElement(CardElement),
            });

            if (error) {
                setErrorMessage(error.message);
                setIsProcessing(false);
                return;
            }

            // Send payment method id to your server
            const response = await apiCall({
                method: 'POST',
                url: routes.api.account.subscriptions(selectedPlan),
                data: {
                    plan_id: selectedPlan,
                    payment_method_id: paymentMethod.id
                },
                successMessage: t('subscriptionSuccess'),
                errorMessage: t('subscriptionError'),
            });

            if (response.data.requires_action) {
                // Use stripe.confirmCardPayment to handle 3D Secure authentication
                const {error} = await stripe.confirmCardPayment(response.data.client_secret);
                if (error) {
                    setErrorMessage(error.message);
                    setIsProcessing(false);
                    return;
                }
            }

            // Payment successful
            onSuccess();
        } catch (error) {
            console.error('Subscription error:', error);
            setErrorMessage(t('subscriptionError'));
        }

        setIsProcessing(false);
    };

    return (
        <form onSubmit={handleSubmit}>
            <CardElement/>
            {errorMessage && <Typography color="error">{errorMessage}</Typography>}
            <Button
                type="submit"
                disabled={!stripe || isProcessing}
                variant="contained"
                color="primary"
                sx={{mt: 2}}
            >
                {isProcessing ? t('processing') : t('subscribe')}
            </Button>
        </form>
    );
};

export default CheckoutForm;