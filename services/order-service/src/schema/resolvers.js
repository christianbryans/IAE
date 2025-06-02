const Order = require('../models/order');
const { fetchProducts } = require('../services/productService');

const resolvers = {
  Query: {
    order: async (_, { id }) => {
      return await Order.findById(id);
    },
    orders: async (_, { userId }) => {
      return await Order.findByUserId(userId);
    }
  },

  Mutation: {
    createOrder: async (_, { input }) => {
      return await Order.create(input);
    },
    updateOrderStatus: async (_, { id, status }) => {
      return await Order.updateStatus(id, status);
    },
    cancelOrder: async (_, { id }) => {
      return await Order.updateStatus(id, 'CANCELLED');
    }
  },

  Order: {
    products: async (order) => {
      const orderItems = await Order.getOrderItems(order.id);
      const productIds = orderItems.map(item => item.product_id);
      return await fetchProducts(productIds);
    }
  }
};

module.exports = resolvers; 