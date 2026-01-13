import * as dotenv from 'dotenv';
console.log("1. Dotenv import: OK");

import { ShopifyClient } from './src/shopify.js';
console.log("2. ShopifyClient import: OK");

import { ImageProcessor } from './src/imageProcessor.js';
console.log("3. ImageProcessor import: OK");

import { ProductScaler } from './src/scaler.js';
console.log("4. ProductScaler import: OK");

dotenv.config();
console.log("5. Dotenv config: OK");
console.log("ALL IMPORTS SUCCESSFUL");
