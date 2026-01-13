import dotenv from 'dotenv';
import { ShopifyClient } from './src/shopify.js';
import { ImageProcessor } from './src/imageProcessor.js';
import { ProductScaler } from './src/scaler.js';
import sharp from 'sharp';
import fs from 'fs/promises';

dotenv.config();

/**
 * Diagnostic tool to analyze what's happening with image processing
 */
class ImageDiagnostics {
  constructor() {
    this.shopify = new ShopifyClient({
      storeUrl: process.env.SHOPIFY_STORE_URL,
      accessToken: process.env.SHOPIFY_ACCESS_TOKEN,
    });

    this.scaler = new ProductScaler(2000, 2500);
    this.outputDir = './diagnostics';
  }

  async run(limit = 10) {
    console.log('=== IMAGE PROCESSING DIAGNOSTICS ===\n');

    await fs.mkdir(this.outputDir, { recursive: true });

    // Get products
    console.log('Fetching products...');
    const products = await this.shopify.getAllProducts();
    const testProducts = products.slice(0, limit);

    console.log(`Analyzing ${testProducts.length} products\n`);

    const report = {
      products: [],
      issues: {
        backgroundRemovalFailed: [],
        whiteBorders: [],
        tinyProducts: [],
        poorScaling: [],
        shadowIssues: []
      }
    };

    for (const product of testProducts) {
      if (!product.images || product.images.length === 0) continue;

      const image = product.images[0];
      console.log(`\n${'='.repeat(60)}`);
      console.log(`ANALYZING: ${product.title}`);
      console.log('='.repeat(60));

      try {
        const analysis = await this.analyzeImage(product, image);
        report.products.push(analysis);

        // Flag issues
        if (analysis.backgroundRemovalFailed) {
          report.issues.backgroundRemovalFailed.push(product.title);
        }
        if (analysis.hasWhiteBorder) {
          report.issues.whiteBorders.push(product.title);
        }
        if (analysis.tooSmall) {
          report.issues.tinyProducts.push(product.title);
        }
        if (analysis.scalingIssue) {
          report.issues.poorScaling.push(product.title);
        }

      } catch (error) {
        console.error(`ERROR: ${error.message}`);
      }
    }

    // Generate report
    await this.generateReport(report);

    console.log('\n' + '='.repeat(60));
    console.log('DIAGNOSTIC SUMMARY');
    console.log('='.repeat(60));
    console.log(`✓ Analyzed ${report.products.length} products`);
    console.log(`✗ Background removal issues: ${report.issues.backgroundRemovalFailed.length}`);
    console.log(`✗ White borders remaining: ${report.issues.whiteBorders.length}`);
    console.log(`✗ Products too small: ${report.issues.tinyProducts.length}`);
    console.log(`✗ Scaling issues: ${report.issues.poorScaling.length}`);
    console.log('\nOpen diagnostics/report.html to see detailed analysis');
  }

  async analyzeImage(product, image) {
    const analysis = {
      title: product.title,
      productType: product.product_type,
      imageUrl: image.src
    };

    // Download original
    console.log('Downloading...');
    const originalBuffer = await this.shopify.downloadImage(image.src);
    const originalMeta = await sharp(originalBuffer).metadata();

    analysis.original = {
      width: originalMeta.width,
      height: originalMeta.height,
      format: originalMeta.format,
      hasAlpha: originalMeta.hasAlpha,
      size: originalBuffer.length
    };

    console.log(`Original: ${originalMeta.width}×${originalMeta.height} ${originalMeta.format}`);
    console.log(`Has alpha: ${originalMeta.hasAlpha}`);

    // Save original
    await fs.writeFile(
      `${this.outputDir}/${product.id}_1_original.${originalMeta.format}`,
      originalBuffer
    );

    // Check for white borders (sample edge pixels)
    const hasWhiteBorder = await this.detectWhiteBorder(originalBuffer);
    analysis.hasWhiteBorder = hasWhiteBorder;
    if (hasWhiteBorder) {
      console.log('⚠️  WHITE BORDER DETECTED');
    }

    // Categorize
    const { category, reason } = this.scaler.categorizeProduct(
      originalMeta.width,
      originalMeta.height,
      product.title,
      product.product_type
    );
    analysis.category = category;
    analysis.categoryReason = reason;
    console.log(`Category: ${category} - ${reason}`);

    // Get scaling info
    const scalingInfo = this.scaler.getScalingInfo(
      originalMeta.width,
      originalMeta.height,
      product.title,
      product.product_type
    );
    analysis.scalingInfo = scalingInfo;
    console.log(`Scale factor: ${(scalingInfo.scaled.scaleFactor * 100).toFixed(1)}%`);

    // Check if too small
    const minDimension = Math.min(originalMeta.width, originalMeta.height);
    analysis.tooSmall = minDimension < 400;
    if (analysis.tooSmall) {
      console.log(`⚠️  VERY SMALL IMAGE: ${minDimension}px`);
    }

    // Check scaling issues
    analysis.scalingIssue = scalingInfo.scaled.scaleFactor > 2.0;
    if (analysis.scalingIssue) {
      console.log(`⚠️  EXTREME UPSCALING: ${(scalingInfo.scaled.scaleFactor * 100).toFixed(0)}%`);
    }

    // Try background removal with ACTUAL AI
    console.log('Testing AI background removal...');
    let backgroundRemoved;
    analysis.backgroundRemovalFailed = false;
    analysis.backgroundRemovalTime = 0;

    try {
      const startTime = Date.now();

      // Import and use the actual AI background removal
      const { removeBackground } = await import('@imgly/background-removal-node');
      const blob = await removeBackground(originalBuffer);

      // Convert Blob to Buffer
      const arrayBuffer = await blob.arrayBuffer();
      backgroundRemoved = Buffer.from(arrayBuffer);

      analysis.backgroundRemovalTime = Date.now() - startTime;
      console.log(`✓ AI background removal OK (${analysis.backgroundRemovalTime}ms)`);

      const removedMeta = await sharp(backgroundRemoved).metadata();

      // Save for comparison
      await fs.writeFile(
        `${this.outputDir}/${product.id}_2_ai_removed.png`,
        backgroundRemoved
      );

      analysis.afterBackgroundRemoval = {
        width: removedMeta.width,
        height: removedMeta.height,
        hasAlpha: removedMeta.hasAlpha,
        changed: originalBuffer.length !== backgroundRemoved.length
      };

    } catch (error) {
      console.log(`✗ AI BACKGROUND REMOVAL FAILED: ${error.message}`);
      analysis.backgroundRemovalFailed = true;
      analysis.backgroundRemovalError = error.message;
      backgroundRemoved = originalBuffer;

      // Save original as "removed" so we can see it failed
      await fs.writeFile(
        `${this.outputDir}/${product.id}_2_ai_removed.png`,
        originalBuffer
      );
    }

    // Check shadow sizing
    const shadowPos = this.scaler.getShadowPosition(
      scalingInfo.scaled.width,
      scalingInfo.scaled.height,
      category
    );
    analysis.shadow = shadowPos;
    console.log(`Shadow: ${shadowPos.width}×${shadowPos.height}px`);

    // Check if shadow is reasonable
    const shadowWidthRatio = shadowPos.width / scalingInfo.scaled.width;
    if (shadowWidthRatio > 2.0 || shadowWidthRatio < 0.5) {
      console.log(`⚠️  SHADOW SIZE ISSUE: ${shadowWidthRatio.toFixed(2)}x product width`);
      analysis.shadowIssue = true;
    }

    return analysis;
  }

  async detectWhiteBorder(buffer) {
    try {
      const image = sharp(buffer);
      const { data, info } = await image
        .raw()
        .toBuffer({ resolveWithObject: true });

      // Sample edge pixels
      const sampleSize = 10;
      let whitePixels = 0;
      const totalSamples = sampleSize * 4; // top, bottom, left, right edges

      // Top edge
      for (let x = 0; x < sampleSize; x++) {
        const idx = (x * info.width) * info.channels;
        const r = data[idx];
        const g = data[idx + 1];
        const b = data[idx + 2];
        if (r > 240 && g > 240 && b > 240) whitePixels++;
      }

      // Check if predominantly white
      return whitePixels / totalSamples > 0.7;

    } catch (error) {
      return false;
    }
  }

  async generateReport(report) {
    const html = `<!DOCTYPE html>
<html>
<head>
  <title>Image Processing Diagnostics</title>
  <style>
    body { font-family: monospace; padding: 20px; background: #1e1e1e; color: #d4d4d4; }
    .product { margin: 20px 0; padding: 20px; background: #252526; border-left: 4px solid #007acc; }
    .error { border-left-color: #f48771; }
    .warning { border-left-color: #ffd700; }
    .ok { border-left-color: #89d185; }
    h1 { color: #4ec9b0; }
    h2 { color: #569cd6; }
    .issue { color: #f48771; margin: 5px 0; }
    .warning-text { color: #ffd700; }
    .ok-text { color: #89d185; }
    pre { background: #1e1e1e; padding: 10px; overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; margin: 10px 0; }
    th, td { border: 1px solid #3e3e42; padding: 8px; text-align: left; }
    th { background: #2d2d30; }
  </style>
</head>
<body>
  <h1>🔍 Image Processing Diagnostics Report</h1>

  <h2>Issues Summary</h2>
  <table>
    <tr><th>Issue Type</th><th>Count</th></tr>
    <tr><td>Background Removal Failed</td><td>${report.issues.backgroundRemovalFailed.length}</td></tr>
    <tr><td>White Borders Remaining</td><td>${report.issues.whiteBorders.length}</td></tr>
    <tr><td>Products Too Small</td><td>${report.issues.tinyProducts.length}</td></tr>
    <tr><td>Scaling Issues</td><td>${report.issues.poorScaling.length}</td></tr>
  </table>

  <h2>Product Analysis</h2>
  ${report.products.map(p => this.generateProductCard(p)).join('\n')}
</body>
</html>`;

    await fs.writeFile(`${this.outputDir}/report.html`, html);
  }

  generateProductCard(p) {
    const hasIssues = p.backgroundRemovalFailed || p.hasWhiteBorder || p.tooSmall || p.scalingIssue || p.shadowIssue;
    const cssClass = hasIssues ? 'error' : 'ok';

    return `
<div class="product ${cssClass}">
  <h3>${p.title}</h3>
  <p><strong>Type:</strong> ${p.productType || 'N/A'}</p>

  <h4>Original Image</h4>
  <ul>
    <li>Dimensions: ${p.original.width}×${p.original.height}</li>
    <li>Format: ${p.original.format}</li>
    <li>Has Alpha: ${p.original.hasAlpha ? 'Yes' : 'No'}</li>
    <li>Size: ${(p.original.size / 1024).toFixed(0)} KB</li>
    ${p.hasWhiteBorder ? '<li class="warning-text">⚠️ White border detected</li>' : ''}
  </ul>

  <h4>AI Background Removal</h4>
  <ul>
    <li>Status: ${p.backgroundRemovalFailed ? '<span class="issue">FAILED</span>' : '<span class="ok-text">SUCCESS</span>'}</li>
    ${p.backgroundRemovalFailed ? `<li class="issue">Error: ${p.backgroundRemovalError || 'Unknown'}</li>` : `<li>Processing time: ${p.backgroundRemovalTime}ms</li>`}
    ${p.afterBackgroundRemoval ? `
    <li>Output: ${p.afterBackgroundRemoval.width}×${p.afterBackgroundRemoval.height}</li>
    <li>Image Changed: ${p.afterBackgroundRemoval.changed ? '<span class="ok-text">Yes</span>' : '<span class="issue">No - IDENTICAL TO ORIGINAL</span>'}</li>
    ` : ''}
  </ul>

  <h4>Categorization</h4>
  <ul>
    <li>Category: <strong>${p.category}</strong></li>
    <li>Reason: ${p.categoryReason}</li>
    <li>Scale Factor: ${(p.scalingInfo.scaled.scaleFactor * 100).toFixed(1)}%</li>
    <li>Final Size: ${p.scalingInfo.scaled.width}×${p.scalingInfo.scaled.height}</li>
  </ul>

  <h4>Shadow</h4>
  <ul>
    <li>Size: ${p.shadow.width}×${p.shadow.height}px</li>
    <li>Ratio to product: ${(p.shadow.width / p.scalingInfo.scaled.width).toFixed(2)}x</li>
  </ul>

  ${hasIssues ? '<h4>⚠️ Issues Detected</h4><ul>' : ''}
  ${p.backgroundRemovalFailed ? `<li class="issue">AI background removal failed: ${p.backgroundRemovalError || 'Unknown error'}</li>` : ''}
  ${p.afterBackgroundRemoval && !p.afterBackgroundRemoval.changed ? '<li class="issue">Background removal had no effect (file size unchanged)</li>' : ''}
  ${p.hasWhiteBorder ? '<li class="issue">White border detected in original</li>' : ''}
  ${p.tooSmall ? '<li class="issue">Original image very small (< 400px)</li>' : ''}
  ${p.scalingIssue ? '<li class="issue">Extreme upscaling required (> 200%)</li>' : ''}
  ${p.shadowIssue ? '<li class="issue">Shadow sizing looks wrong</li>' : ''}
  ${hasIssues ? '</ul>' : ''}
</div>`;
  }
}

// Run diagnostics
const limit = process.argv[2] ? parseInt(process.argv[2]) : 10;
console.log(`Running diagnostics on ${limit} products...\n`);

const diagnostics = new ImageDiagnostics();
diagnostics.run(limit).catch(error => {
  console.error('Diagnostics failed:', error);
  process.exit(1);
});
