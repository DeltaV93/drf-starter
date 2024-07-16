# Subscription and Payment Management System

This Django Rest Framwork + React application provides a robust system for managing subscriptions and payments using Stripe. It's designed to handle user subscriptions, add-ons, invoicing, and payment processing.

## Features

- User authentication and registration
- Subscription management (create, update, cancel)
- Add-on management for subscriptions
- Invoicing system with PDF generation
- Stripe integration for payment processing
- Asynchronous task processing with Celery
- Comprehensive logging system
- Rate limiting and throttling
- GDPR-compliant user data management
- SES email workflow
- Docker build

## Prerequisites

- Python 3.8+
- PostgreSQL
- Redis (for Celery)
- Stripe account
- SES account with AWS
- Docker

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/your-repo-name.git`
cd your-repo-name
```
2. Create a virtual environment and activate it:
```
python -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
```

3. Install the required packages:
```
pip install -r requirements.txt
```
4. Set up your environment variables:
Create a `.env` file in the project root and add the following:
```
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgres://user:password@localhost/dbname
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
REDIS_URL=redis://localhost:6379
```

5. Run migrations:
```
python manage.py migrate
```

6. Start the development server:

```
python manage.py runserver
```

## Running Celery

To run Celery for asynchronous task processing:
```
celery -A your_project_name worker -l info
```

## Running Tests

To run the test suite:
```
python manage.py test
```

## API Documentation

API documentation is available at `/api/docs/` when the server is running.

## Deployment

For production deployment:

1. Set `DEBUG=False` in your environment variables.
2. Use a production-grade server like Gunicorn.
3. Set up a reverse proxy with Nginx.
4. Ensure all sensitive data is properly secured.
5. Set up SSL certificates for HTTPS.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Acknowledgments

- Django and Django Rest Framework communities
- Stripe for payment processing
- All other open-source libraries used in this project
