const { ApolloClient, InMemoryCache, gql } = require('@apollo/client');
const fetch = require('node-fetch');

const client = new ApolloClient({
  uri: process.env.PRODUCT_SERVICE_URL,
  cache: new InMemoryCache(),
  fetch
});

const GET_PRODUCTS = gql`
  query GetProducts($ids: [ID!]!) {
    products(ids: $ids) {
      id
      name
      price
    }
  }
`;

async function fetchProducts(productIds) {
  try {
    const { data } = await client.query({
      query: GET_PRODUCTS,
      variables: { ids: productIds }
    });
    return data.products;
  } catch (error) {
    console.error('Error fetching products:', error);
    throw new Error('Failed to fetch products from Product Service');
  }
}

module.exports = {
  fetchProducts
}; 