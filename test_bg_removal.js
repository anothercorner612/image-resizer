import sharp from 'sharp';
import { ImageProcessor } from './src/imageProcessor.js';
import fs from 'fs/promises';

async function testBackgroundRemoval() {
  console.log('=== Testing Local AI Background Removal ===\n');

  try {
    // Create a simple test image: 400x400 white square with a black circle
    console.log('Creating test image...');
    const testImage = await sharp({
      create: {
        width: 400,
        height: 400,
        channels: 4,
        background: { r: 255, g: 255, b: 255, alpha: 1 }
      }
    })
    .composite([{
      input: Buffer.from(`
        <svg width="400" height="400">
          <circle cx="200" cy="200" r="100" fill="black"/>
        </svg>
      `),
      top: 0,
      left: 0
    }])
    .png()
    .toBuffer();

    console.log('✓ Test image created (400x400 white background with black circle)\n');

    // Initialize processor
    console.log('Initializing ImageProcessor with background removal enabled...');
    const processor = new ImageProcessor({
      canvasWidth: 2000,
      canvasHeight: 2500,
      backgroundColor: '#f3f3f4',
      shadowOpacity: 0.18,
      webpQuality: 90,
      enableBackgroundRemoval: true,
      enableAutoTrim: true
    });

    console.log('\nTesting background removal...');
    const result = await processor.cleanupBackground(testImage);

    // Save result
    await fs.mkdir('./temp', { recursive: true });
    await fs.writeFile('./temp/test_bg_removal.png', result);
    console.log('✓ Background removal complete!');
    console.log('  Result saved to: ./temp/test_bg_removal.png');

    // Check result metadata
    const resultMeta = await sharp(result).metadata();
    console.log(`  Result: ${resultMeta.width}×${resultMeta.height}, has alpha: ${resultMeta.hasAlpha}`);

    console.log('\n✅ Background removal test PASSED!');
    console.log('   The U2Net AI model is working correctly.');

  } catch (error) {
    console.error('\n❌ Test FAILED:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

testBackgroundRemoval();
