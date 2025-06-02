require('dotenv').config();
const { ApolloServer } = require('@apollo/server');
const { buildSubgraphSchema } = require('@apollo/subgraph');
const { expressMiddleware } = require('@apollo/server/express4');
const express = require('express');
const cors = require('cors');
const { readFileSync } = require('fs');
const path = require('path');
const resolvers = require('./schema/resolvers');

const app = express();
app.use(cors());
app.use(express.json());

// Read GraphQL schema
const typeDefs = readFileSync(
  path.join(__dirname, 'schema', 'typeDefs.graphql'),
  'utf8'
);

// Create Apollo Server
const server = new ApolloServer({
  schema: buildSubgraphSchema({
    typeDefs,
    resolvers
  })
});

// Start server
async function startServer() {
  await server.start();

  app.use(
    '/graphql',
    expressMiddleware(server, {
      context: async ({ req }) => {
        // Add any context data here
        return {};
      }
    })
  );

  const PORT = process.env.PORT || 4001;
  app.listen(PORT, () => {
    console.log(`Order Service running at http://localhost:${PORT}/graphql`);
  });
}

startServer().catch(err => {
  console.error('Error starting server:', err);
  process.exit(1);
}); 