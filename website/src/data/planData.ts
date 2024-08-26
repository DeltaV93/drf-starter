export interface Plan {
    id: string;
    name: string;
    description: string;
    price: number;
    features: string[];
}
//
export const plans: Plan[] = [
    {
        id: import.meta.env.VITE_APP_STRIPE_SUB_BASIC,
        name: 'Basic',
        description: 'Great for starters',
        price: 550.00,
        features: ['Feature 1', 'Feature 2', 'Feature 3'],
    },
    {
        id: import.meta.env.VITE_APP_STRIPE_SUB_STANDARD,
        name: 'Standard',
        description: 'Perfect for professionals',
        price: 850.00,
        features: ['Feature 1', 'Feature 2', 'Feature 3', 'Feature 4', 'Feature 5'],
    },
    {
        id: import.meta.env.VITE_APP_STRIPE_SUB_PREMIUM,
        name: 'Premium',
        description: 'For large organizations',
        price: 1500.00,
        features: ['Feature 1', 'Feature 2', 'Feature 3', 'Feature 4', 'Feature 5', 'Feature 6', 'Feature 7'],
    },
];