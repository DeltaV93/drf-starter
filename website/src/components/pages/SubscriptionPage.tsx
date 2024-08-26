import React, {useState} from 'react';
import {
    Box,
    Button,
    Card,
    CardContent,
    Container,
    Grid,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Typography
} from '@mui/material';
// import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import {useTranslation} from 'react-i18next';
import {Plan, plans} from '../../data/planData';
import PaymentForm from "../common/PaymentForm.tsx";
import {loadStripe} from "@stripe/stripe-js";
import {Elements} from "@stripe/react-stripe-js";
import {apiCall} from "../../utils/api.tsx";
import {routes} from "../../libs/routes.ts";

const stripePromise = loadStripe(import.meta.env.VITE_APP_STRIPE_PUBLISHABLE_KEY);

const SubscriptionPage: React.FC = () => {
    const {t} = useTranslation();
    const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);

    const handleSelectPlan = (plan: Plan) => {
        setSelectedPlan(plan);
    };

    const handlePaymentSubmit = async (paymentDetails: any) => {
        // Handle payment submission logic here
        const url = routes.api.account.subscriptions(selectedPlan?.id)
        console.log(url)
        try {
            const response = await apiCall({
                url: url,
                method: 'POST',
                data: paymentDetails,
                successMessage: t('subscriptionSuccess'),
                errorMessage: t('subscriptionError'),
                useCsrfToken: true,
                withCredentials: true,
            });
            console.log('Payment submitted:', paymentDetails, response);
        } catch (error) {
            console.error('Login error:', error);
            // Handle error (show toast, etc.)
        }
    };

    if (!selectedPlan) {
        return (
            <Container maxWidth="lg">
                <Box sx={{mt: 8, mb: 4}}>
                    <Typography variant="h4" align="center" gutterBottom>
                        {t('selectSubscription')}
                    </Typography>
                    <Grid container spacing={3} justifyContent="center">
                        {plans.map((plan) => (
                            <Grid item xs={12} sm={6} md={4} key={plan.id}>
                                <Card>
                                    <CardContent>
                                        <Typography variant="h5" component="div" gutterBottom>
                                            {plan.name}
                                        </Typography>
                                        <Typography variant="h4" color="primary" gutterBottom>
                                            ${plan.price.toFixed(2)}/mo
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary" gutterBottom>
                                            {plan.description}
                                        </Typography>
                                        <List dense>
                                            {plan.features.map((feature, index) => (
                                                <ListItem key={index}>
                                                    <ListItemIcon>
                                                        {/*<CheckIcon color="primary" />*/}
                                                    </ListItemIcon>
                                                    <ListItemText primary={feature}/>
                                                </ListItem>
                                            ))}
                                        </List>
                                        <Button
                                            variant="contained"
                                            color="primary"
                                            fullWidth
                                            onClick={() => handleSelectPlan(plan)}
                                        >
                                            {t('selectPlan')}
                                        </Button>
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                </Box>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg">
            <Box sx={{mt: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
                {selectedPlan && (
                    <Elements stripe={stripePromise}>
                        <PaymentForm
                            selectedPlanId={selectedPlan.id}
                            amount={selectedPlan.price}
                            onPaymentSubmit={handlePaymentSubmit}
                        />
                    </Elements>
                )}

                <Card sx={{width: 300, ml: 4}}>
                    <CardContent>
                        <Typography variant="h5" gutterBottom>
                            {selectedPlan.name}
                        </Typography>
                        <Typography variant="h3" color="primary" gutterBottom>
                            ${selectedPlan.price.toFixed(2)}/mo
                        </Typography>

                        <List dense>
                            {selectedPlan.features.map((feature, index) => (
                                <ListItem key={index}>
                                    <ListItemIcon>
                                        {/*<CheckIcon color="primary" />*/}
                                    </ListItemIcon>
                                    <ListItemText primary={feature}/>
                                </ListItem>
                            ))}
                        </List>

                        <Box sx={{mt: 2}}>
                            <Typography variant="subtitle1" sx={{display: 'flex', alignItems: 'center', mb: 1}}>
                                {/*<CheckCircleOutlineIcon color="primary" sx={{ mr: 1 }} />*/}
                                {t('paymentAndInvoice')}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                {t('paymentDescription')}
                            </Typography>
                        </Box>

                        <Box sx={{mt: 2}}>
                            <Typography variant="subtitle1" sx={{display: 'flex', alignItems: 'center', mb: 1}}>
                                {/*<CheckCircleOutlineIcon color="primary" sx={{ mr: 1 }} />*/}
                                {t('discountsAndOffers')}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                {t('discountsDescription')}
                            </Typography>
                        </Box>

                        <Typography variant="body2" sx={{mt: 2, p: 1, bgcolor: 'grey.100', borderRadius: 1}}>
                            {t('guaranteedForYears', {years: 5})}
                        </Typography>

                        <Button
                            variant="outlined"
                            color="primary"
                            fullWidth
                            onClick={() => setSelectedPlan(null)}
                            sx={{mt: 2}}
                        >
                            {t('changePlan')}
                        </Button>
                    </CardContent>
                </Card>
            </Box>
        </Container>
    );
};

export default SubscriptionPage;