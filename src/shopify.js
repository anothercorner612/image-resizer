import '@shopify/shopify-api/adapters/node';
import { shopifyApi, LATEST_API_VERSION } from '@shopify/shopify-api';
import axios from 'axios';

/**
 * Shopify API Client for product and image operations
 */
export class ShopifyClient {
  constructor(config) {
    this.storeUrl = config.storeUrl;
    this.accessToken = config.accessToken;

    // Initialize Shopify API
    this.shopify = shopifyApi({
      apiSecretKey: this.accessToken,
      apiVersion: LATEST_API_VERSION,
      isCustomStoreApp: true,
      adminApiAccessToken: this.accessToken,
      isEmbeddedApp: false,
      hostName: this.storeUrl.replace('https://', '').replace('http://', ''),
    });

    // Create axios instance for direct API calls
    this.api = axios.create({
      baseURL: `https://${this.storeUrl}/admin/api/${LATEST_API_VERSION}`,
      headers: {
        'X-Shopify-Access-Token': this.accessToken,
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Get all products with pagination support
   * @param {Object} options - Query options
   * @returns {Promise<Array>} Array of all products
   */
  async getAllProducts(options = {}) {
    const limit = options.limit || 250;
    let allProducts = [];
    let pageInfo = null;
    let hasNextPage = true;

    console.log('Fetching all products from Shopify...');

    while (hasNextPage) {
      try {
        const params = {
          limit,
          fields: 'id,title,product_type,images,handle',
        };

        if (pageInfo) {
          params.page_info = pageInfo;
        }

        const response = await this.api.get('/products.json', { params });
        const products = response.data.products || [];

        allProducts = allProducts.concat(products);
        console.log(`Fetched ${products.length} products (total: ${allProducts.length})`);

        // Check for pagination
        const linkHeader = response.headers.link;
        if (linkHeader && linkHeader.includes('rel="next"')) {
          const nextMatch = linkHeader.match(/<[^>]*page_info=([^>&]+)[^>]*>;\s*rel="next"/);
          if (nextMatch) {
            pageInfo = nextMatch[1];
          } else {
            hasNextPage = false;
          }
        } else {
          hasNextPage = false;
        }

        // Rate limiting delay
        await this.delay(500);

      } catch (error) {
        console.error('Error fetching products:', error.response?.data || error.message);
        throw error;
      }
    }

    console.log(`Total products fetched: ${allProducts.length}`);
    return allProducts;
  }

  /**
   * Get a single product by ID
   * @param {string|number} productId - Product ID
   * @returns {Promise<Object>} Product data
   */
  async getProduct(productId) {
    try {
      const response = await this.api.get(`/products/${productId}.json`);
      return response.data.product;
    } catch (error) {
      console.error(`Error fetching product ${productId}:`, error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * Get product images
   * @param {string|number} productId - Product ID
   * @returns {Promise<Array>} Array of images
   */
  async getProductImages(productId) {
    try {
      const product = await this.getProduct(productId);
      return product.images || [];
    } catch (error) {
      console.error(`Error fetching images for product ${productId}:`, error.message);
      throw error;
    }
  }

  /**
   * Update a product image
   * @param {string|number} productId - Product ID
   * @param {string|number} imageId - Image ID
   * @param {Object} data - Image data to update
   * @returns {Promise<Object>} Updated image data
   */
  async updateProductImage(productId, imageId, data) {
    try {
      const response = await this.api.put(
        `/products/${productId}/images/${imageId}.json`,
        { image: data }
      );
      return response.data.image;
    } catch (error) {
      console.error(`Error updating image ${imageId}:`, error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * Upload a new product image
   * @param {string|number} productId - Product ID
   * @param {Object} data - Image data (attachment, src, etc.)
   * @returns {Promise<Object>} Uploaded image data
   */
  async uploadProductImage(productId, data) {
    try {
      const response = await this.api.post(
        `/products/${productId}/images.json`,
        { image: data }
      );
      return response.data.image;
    } catch (error) {
      console.error(`Error uploading image to product ${productId}:`, error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * Download an image from URL to buffer
   * @param {string} url - Image URL
   * @returns {Promise<Buffer>} Image buffer
   */
  async downloadImage(url) {
    try {
      const response = await axios.get(url, {
        responseType: 'arraybuffer',
        timeout: 30000,
      });
      return Buffer.from(response.data);
    } catch (error) {
      console.error(`Error downloading image from ${url}:`, error.message);
      throw error;
    }
  }

  /**
   * Delay helper for rate limiting
   * @param {number} ms - Milliseconds to delay
   * @returns {Promise}
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get product metafields
   * @param {string|number} productId - Product ID
   * @param {string} namespace - Metafield namespace
   * @param {string} key - Metafield key
   * @returns {Promise<Object|null>} Metafield data or null
   */
  async getMetafield(productId, namespace, key) {
    try {
      const response = await this.api.get(`/products/${productId}/metafields.json`, {
        params: { namespace, key }
      });
      const metafields = response.data.metafields || [];
      return metafields.length > 0 ? metafields[0] : null;
    } catch (error) {
      console.error(`Error fetching metafield for product ${productId}:`, error.response?.data || error.message);
      return null;
    }
  }

  /**
   * Create or update a product metafield
   * @param {string|number} productId - Product ID
   * @param {string} namespace - Metafield namespace
   * @param {string} key - Metafield key
   * @param {any} value - Metafield value
   * @param {string} type - Metafield type (default: json)
   * @returns {Promise<Object>} Metafield data
   */
  async setMetafield(productId, namespace, key, value, type = 'json') {
    try {
      // Check if metafield exists
      const existing = await this.getMetafield(productId, namespace, key);

      const metafieldData = {
        namespace,
        key,
        value: typeof value === 'string' ? value : JSON.stringify(value),
        type,
      };

      let response;
      if (existing) {
        // Update existing metafield
        response = await this.api.put(
          `/products/${productId}/metafields/${existing.id}.json`,
          { metafield: metafieldData }
        );
      } else {
        // Create new metafield
        response = await this.api.post(
          `/products/${productId}/metafields.json`,
          { metafield: metafieldData }
        );
      }

      return response.data.metafield;
    } catch (error) {
      console.error(`Error setting metafield for product ${productId}:`, error.response?.data || error.message);
      throw error;
    }
  }

  /**
   * Delete a product image
   * @param {string|number} productId - Product ID
   * @param {string|number} imageId - Image ID
   * @returns {Promise<void>}
   */
  async deleteProductImage(productId, imageId) {
    try {
      await this.api.delete(`/products/${productId}/images/${imageId}.json`);
    } catch (error) {
      console.error(`Error deleting image ${imageId}:`, error.response?.data || error.message);
      throw error;
    }
  }
}
