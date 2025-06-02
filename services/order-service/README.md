# Order Service

This service handles order management in the EAI microservices architecture.

## Features

- Create new orders
- Update order status
- Cancel orders
- View order details
- List user orders
- Integration with Product Service

## API Documentation

### Queries

#### Get Order by ID
```graphql
query {
  order(id: "123") {
    id
    userId
    products {
      id
      name
      price
    }
    total
    status
    createdAt
    updatedAt
  }
}
```

#### Get User Orders
```graphql
query {
  orders(userId: "456") {
    id
    products {
      id
      name
      price
    }
    total
    status
    createdAt
  }
}
```

### Mutations

#### Create Order
```graphql
mutation {
  createOrder(input: {
    userId: "456"
    productIds: ["123", "124", "125"]
  }) {
    id
    status
    total
  }
}
```

#### Update Order Status
```graphql
mutation {
  updateOrderStatus(
    id: "123"
    status: PROCESSING
  ) {
    id
    status
    updatedAt
  }
}
```

#### Cancel Order
```graphql
mutation {
  cancelOrder(id: "123") {
    id
    status
    updatedAt
  }
}
```

## Database Schema

### Orders Table
```sql
CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL,
  total DECIMAL(10,2) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Order Items Table
```sql
CREATE TABLE order_items (
  id SERIAL PRIMARY KEY,
  order_id INTEGER REFERENCES orders(id),
  product_id VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Environment Variables

- `PORT`: Service port (default: 4001)
- `DATABASE_URL`: PostgreSQL connection string
- `PRODUCT_SERVICE_URL`: URL of the Product Service

## Dependencies

- Node.js 18+
- PostgreSQL 14+
- Apollo Server
- GraphQL
- Express

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Start the service:
   ```bash
   npm start
   ```

## Development

Run in development mode with hot reload:
```bash
npm run dev
```

## Testing

Run tests:
```bash
npm test
```

## Service Dependencies

This service depends on:
- Product Service: For fetching product details
- User Service: For user validation
- Payment Service: For payment processing

## Error Handling

The service implements proper error handling for:
- Database connection issues
- Invalid input data
- Service communication failures
- Transaction rollbacks

## Monitoring

The service exposes health check endpoint at `/health` and includes logging for:
- Request/Response
- Errors
- Performance metrics 