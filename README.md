# S14 Partner Metrics Service

Partner Metrics Service (S14) for the Telcenter Partner system. This microservice aggregates and provides real-time metrics for Partner Portal users.

## Overview

This service operates in two modes:
1. **Real-time metrics collection** via RabbitMQ events from S08 Core Metrics Service (background processing)
2. **HTTP REST API** for on-demand queries from Partner Portal

## Features

### Metrics Provided

1. **Total Active Conversations** (H30.1)
   - Total conversations for this partner
   - Conversations by status: texting, calling, forwarding

2. **Customer Satisfaction Rate** (H30.2)
   - Distribution of satisfaction ratings (1-5 stars)
   - Average satisfaction rating
   - Total rated conversations

3. **Partner Offload Rate** (H30.3)
   - AI success rate (conversations handled without forwarding)
   - Partner intervention rate (AI failures)
   - Overall offload percentage

### APIs

#### HTTP REST API (H30)
- `GET /api/v1/partner/metrics/conversations` - Conversation statistics
- `GET /api/v1/partner/metrics/satisfaction-rate` - Satisfaction metrics
- `GET /api/v1/partner/metrics/offload-rate` - Offload rate metrics
- `GET /api/v1/partner/metrics/health` - Service health check

All endpoints require JWT authentication (Bearer token).

#### RabbitMQ Event Consumer (A17a)
Consumes real-time events from S08:
- `conversation_start_by_partner` - New conversation started
- `conversation_changed_status_by_partner` - Status change
- `conversation_satisfaction_change_by_partner` - Rating updated

#### RabbitMQ Method Caller (A17b)
Calls S08 methods for historical data:
- `get_partner_conversation_statistics` - Get conversation stats
- `get_partner_satisfaction_distribution` - Get satisfaction data

## Installation & Setup

### Prerequisites
- Python 3.12+
- RabbitMQ server
- Access to S08 Core Metrics Service
- Access to Identity Service (for JWT verification)

### Installation

1. Clone the repository
2. Create virtual environment and install dependencies:
```bash
uv venv
uv pip install -e .
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Configuration

Edit `.env` file with the following required variables:

```env
# Partner ID (REQUIRED)
PARTNER_ID=partner_abc123

# Flask Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5014
FLASK_DEBUG=False

# RabbitMQ Configuration
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
S08_EVENTS_QUEUE=s08_events_queue
S14_S08_REQUESTS_QUEUE=s14_s08_requests_queue
S14_S08_RESPONSES_QUEUE=s14_s08_responses_queue

# Authentication
IDENTITY_SERVICE_URL=http://localhost:5001
JWKS_TTL_IN_MINUTES=10
```

## Running the Service

```bash
python -m app
```

## API Usage Examples

### 1. Get Conversation Metrics

```bash
curl -X GET "http://localhost:5014/api/v1/partner/metrics/conversations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. Get Satisfaction Rate

```bash
curl -X GET "http://localhost:5014/api/v1/partner/metrics/satisfaction-rate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. Get Offload Rate

```bash
curl -X GET "http://localhost:5014/api/v1/partner/metrics/offload-rate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Health Check

```bash
curl -X GET "http://localhost:5014/api/v1/partner/metrics/health"
```

## Project Structure

```
telcenter-base-service/
 app/
    __main__.py                    # Main entry point
    controllers/v1/
       partner_metrics.py         # H30 HTTP API endpoints
    services/
       MessageQueueService.py     # RabbitMQ communication
       PartnerMetricsService.py   # Core metrics service
    utils/
        auth.py                     # JWT authentication
 docs/                              # API documentation
 .env.example                       # Example environment configuration
 pyproject.toml                     # Python dependencies
```

## Authentication

This service uses JWT-based authentication with JWKS verification:
- Token Format: Bearer token in Authorization header
- Algorithm: RS256
- JWKS Source: Identity Service
- See docs/auth/VERIFY.md for details

## Dependencies

- `flask` - HTTP server
- `pika` - RabbitMQ client
- `pyjwt` - JWT verification
- `requests` - HTTP client
- `python-dotenv` - Environment management
