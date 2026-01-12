/**
 * Metafield Manager for tracking product harmonization status
 * Uses metafields (NOT tags) to track processing progress
 */
export class MetafieldManager {
  constructor(shopifyClient) {
    this.client = shopifyClient;
    this.namespace = 'automation';
    this.key = 'harmonized';
  }

  /**
   * Get metafield value for a product
   * @param {string|number} productId - Product ID
   * @returns {Promise<Object|null>} Metafield value or null
   */
  async getMetafield(productId) {
    try {
      const metafield = await this.client.getMetafield(productId, this.namespace, this.key);
      if (!metafield) {
        return null;
      }

      // Parse JSON value
      try {
        return JSON.parse(metafield.value);
      } catch (e) {
        console.warn(`Failed to parse metafield value for product ${productId}`);
        return null;
      }
    } catch (error) {
      console.error(`Error getting metafield for product ${productId}:`, error.message);
      return null;
    }
  }

  /**
   * Set metafield value for a product
   * @param {string|number} productId - Product ID
   * @param {Object} value - Metafield value object
   * @returns {Promise<Object>} Metafield data
   */
  async setMetafield(productId, value) {
    try {
      return await this.client.setMetafield(
        productId,
        this.namespace,
        this.key,
        value,
        'json'
      );
    } catch (error) {
      console.error(`Error setting metafield for product ${productId}:`, error.message);
      throw error;
    }
  }

  /**
   * Check if a product has been harmonized
   * @param {string|number} productId - Product ID
   * @returns {Promise<boolean>} True if harmonized
   */
  async isHarmonized(productId) {
    const metafield = await this.getMetafield(productId);
    return metafield && metafield.status === 'completed';
  }

  /**
   * Mark a product as harmonized (completed)
   * @param {string|number} productId - Product ID
   * @param {Object} details - Processing details
   * @returns {Promise<Object>} Metafield data
   */
  async markAsHarmonized(productId, details = {}) {
    const value = {
      status: 'completed',
      processedAt: new Date().toISOString(),
      productTitle: details.productTitle || '',
      processedImages: details.processedImages || [],
      category: details.category || 'unknown',
      scaledDimensions: details.scaledDimensions || {},
    };

    console.log(`✓ Marking product ${productId} as harmonized`);
    return await this.setMetafield(productId, value);
  }

  /**
   * Mark a product as in progress
   * @param {string|number} productId - Product ID
   * @param {Object} details - Processing details
   * @returns {Promise<Object>} Metafield data
   */
  async markAsInProgress(productId, details = {}) {
    const value = {
      status: 'in_progress',
      startedAt: new Date().toISOString(),
      productTitle: details.productTitle || '',
    };

    console.log(`→ Marking product ${productId} as in progress`);
    return await this.setMetafield(productId, value);
  }

  /**
   * Mark a product as failed
   * @param {string|number} productId - Product ID
   * @param {Error|string} error - Error object or message
   * @param {Object} details - Processing details
   * @returns {Promise<Object>} Metafield data
   */
  async markAsFailed(productId, error, details = {}) {
    const value = {
      status: 'failed',
      failedAt: new Date().toISOString(),
      productTitle: details.productTitle || '',
      error: error instanceof Error ? error.message : String(error),
      errorStack: error instanceof Error ? error.stack : undefined,
    };

    console.log(`✗ Marking product ${productId} as failed: ${value.error}`);
    return await this.setMetafield(productId, value);
  }

  /**
   * Get products that need harmonization
   * @param {Array} allProducts - Array of all products
   * @returns {Promise<Array>} Products needing harmonization
   */
  async getProductsNeedingHarmonization(allProducts) {
    console.log('\nChecking harmonization status...');
    const needsHarmonization = [];

    for (const product of allProducts) {
      try {
        const metafield = await this.getMetafield(product.id);

        if (!metafield || metafield.status !== 'completed') {
          needsHarmonization.push(product);
        }

        // Rate limiting
        await this.delay(100);
      } catch (error) {
        console.error(`Error checking product ${product.id}:`, error.message);
        // Include product if we can't check its status
        needsHarmonization.push(product);
      }
    }

    console.log(`${needsHarmonization.length} products need harmonization`);
    return needsHarmonization;
  }

  /**
   * Get statistics about product harmonization
   * @param {Array} allProducts - Array of all products
   * @returns {Promise<Object>} Statistics object
   */
  async getStatistics(allProducts) {
    const stats = {
      total: allProducts.length,
      completed: 0,
      inProgress: 0,
      failed: 0,
      pending: 0,
    };

    console.log('\nCollecting harmonization statistics...');

    for (const product of allProducts) {
      try {
        const metafield = await this.getMetafield(product.id);

        if (!metafield) {
          stats.pending++;
        } else {
          switch (metafield.status) {
            case 'completed':
              stats.completed++;
              break;
            case 'in_progress':
              stats.inProgress++;
              break;
            case 'failed':
              stats.failed++;
              break;
            default:
              stats.pending++;
          }
        }

        // Rate limiting
        await this.delay(100);
      } catch (error) {
        console.error(`Error getting stats for product ${product.id}:`, error.message);
        stats.pending++;
      }
    }

    return stats;
  }

  /**
   * Reset harmonization status for a product
   * @param {string|number} productId - Product ID
   * @returns {Promise<Object>} Metafield data
   */
  async resetStatus(productId) {
    const value = {
      status: 'pending',
      resetAt: new Date().toISOString(),
    };

    console.log(`⟲ Resetting status for product ${productId}`);
    return await this.setMetafield(productId, value);
  }

  /**
   * Get all products with a specific status
   * @param {Array} allProducts - Array of all products
   * @param {string} status - Status to filter by (completed, in_progress, failed, pending)
   * @returns {Promise<Array>} Filtered products
   */
  async getProductsByStatus(allProducts, status) {
    const filtered = [];

    for (const product of allProducts) {
      try {
        const metafield = await this.getMetafield(product.id);

        if (status === 'pending' && !metafield) {
          filtered.push(product);
        } else if (metafield && metafield.status === status) {
          filtered.push(product);
        }

        // Rate limiting
        await this.delay(100);
      } catch (error) {
        console.error(`Error checking product ${product.id}:`, error.message);
      }
    }

    return filtered;
  }

  /**
   * Delay helper
   * @param {number} ms - Milliseconds to delay
   * @returns {Promise}
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
