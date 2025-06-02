const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

class Order {
  static async create({ userId, productIds }) {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      // Create order
      const orderResult = await client.query(
        'INSERT INTO orders (user_id, status, total) VALUES ($1, $2, $3) RETURNING *',
        [userId, 'PENDING', 0]
      );
      const order = orderResult.rows[0];

      // Create order items
      for (const productId of productIds) {
        await client.query(
          'INSERT INTO order_items (order_id, product_id) VALUES ($1, $2)',
          [order.id, productId]
        );
      }

      await client.query('COMMIT');
      return order;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  static async findById(id) {
    const result = await pool.query(
      'SELECT * FROM orders WHERE id = $1',
      [id]
    );
    return result.rows[0];
  }

  static async findByUserId(userId) {
    const result = await pool.query(
      'SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC',
      [userId]
    );
    return result.rows;
  }

  static async updateStatus(id, status) {
    const result = await pool.query(
      'UPDATE orders SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING *',
      [status, id]
    );
    return result.rows[0];
  }

  static async getOrderItems(orderId) {
    const result = await pool.query(
      'SELECT * FROM order_items WHERE order_id = $1',
      [orderId]
    );
    return result.rows;
  }
}

module.exports = Order; 