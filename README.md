# Shopify Image Automation

Automated product image harmonization system for Another Corner's Shopify store. This Node.js automation script processes product images to create consistent backgrounds, intelligent scaling, and professional contact shadows.

## Features

- **Consistent Canvas**: All images standardized to 2000×2500px with #f3f3f4 background
- **Intelligent Scaling**: Automatic categorization and conditional scaling based on product dimensions
- **Contact Shadows**: Professional 18% opacity shadows positioned at product base
- **WebP Output**: Optimized WebP format at 90% quality for fast loading
- **Metafield Tracking**: Progress tracking using Shopify metafields (not tags)
- **Batch Processing**: Concurrent processing with rate limiting
- **Test Suite**: Visual comparison HTML for quality verification
- **Dry Run Mode**: Test without uploading to Shopify

## Visual Specifications

- **Canvas Size**: 2000 × 2500 pixels (0.8 aspect ratio)
- **Background Color**: #f3f3f4 (exact match to site whitespace)
- **Output Format**: WebP at 90% quality
- **Shadow**: Contact shadow with 18% opacity, Gaussian blur, positioned at product base

## Conditional Scaling Rules

The system automatically categorizes products and applies appropriate scaling:

| Category | Detection Rule | Scaling |
|----------|---------------|---------|
| **Tall/Thin** | Aspect ratio < 0.5 (height > 2× width) | 85% of canvas height |
| **Wide** | Aspect ratio > 1.5 (width > 1.5× height) | 82% of canvas width |
| **Small/Accessory** | Longest side < 500px OR keywords (pin, badge, sticker, card, bookmark, keychain, magnet, patch, button) | 50% of canvas height |
| **Default** | Everything else | 82% of longest side |

## Project Structure

```
image-resizer/
├── src/
│   ├── shopify.js           # Shopify API client
│   ├── metafields.js        # Metafield tracking manager
│   ├── scaler.js            # Product categorization & scaling logic
│   ├── imageProcessor.js    # Image processing with Sharp
│   └── main.js              # Main automation orchestrator
├── test_run.js              # Testing suite
├── CHECKLIST.md             # Quality verification checklist
├── README.md                # This file
├── package.json             # Dependencies and scripts
├── .env.example             # Environment variables template
└── .gitignore               # Git ignore rules
```

## Installation

### Prerequisites

- Node.js 18+
- npm or yarn
- Shopify Admin API access token

### Setup

1. Clone the repository:
```bash
git clone https://github.com/anothercorner612/image-resizer.git
cd image-resizer
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:
```bash
cp .env.example .env
```

4. Edit `.env` with your Shopify credentials:
```bash
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your_admin_api_access_token
```

## Usage

### Testing (Recommended First Step)

Run the test suite to generate comparison HTML:

```bash
npm test
```

This will:
- Find one example product of each category
- Process images locally (no upload)
- Generate `comparison.html` for visual review
- Save examples to `output/` directory

Open `comparison.html` in your browser to review the results and verify quality using the embedded checklist.

### Dry Run

Test the automation without uploading to Shopify:

```bash
# Ensure DRY_RUN=true in .env
npm start
```

Process only a limited number of products:
```bash
npm start -- --limit 10
```

### Production Run

After verifying test results and dry run:

```bash
# Set DRY_RUN=false in .env
npm start
```

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Required
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your_admin_api_access_token

# Canvas Configuration (default values shown)
CANVAS_WIDTH=2000
CANVAS_HEIGHT=2500

# Visual Settings
BACKGROUND_COLOR=#f3f3f4
SHADOW_OPACITY=0.18

# Processing Configuration
DRY_RUN=true                    # Set to false for production
MAX_CONCURRENT_PROCESSES=5      # Concurrent image processing limit
```

## Metafield Tracking

The system uses Shopify metafields (NOT tags) to track processing status:

- **Namespace**: `automation`
- **Key**: `harmonized`
- **Type**: JSON

### Metafield Structure

```json
{
  "status": "completed|in_progress|failed",
  "processedAt": "2024-01-12T10:30:00.000Z",
  "productTitle": "Product Name",
  "category": "tall_thin|wide|small_accessory|default",
  "processedImages": [
    {
      "originalId": "123456",
      "category": "default",
      "dimensions": { "width": 1640, "height": 2050 },
      "processedAt": "2024-01-12T10:30:00.000Z"
    }
  ],
  "scaledDimensions": { "width": 1640, "height": 2050 }
}
```

### Status Values

- **completed**: Product successfully harmonized
- **in_progress**: Currently being processed
- **failed**: Processing failed (error details included)
- **pending**: Not yet processed (no metafield)

## API Components

### ShopifyClient (src/shopify.js)

Handles all Shopify API operations:
- `getAllProducts()` - Fetch all products with pagination
- `getProduct(id)` - Get single product
- `getProductImages(id)` - Get product images
- `updateProductImage(productId, imageId, data)` - Update image
- `uploadProductImage(productId, data)` - Upload new image
- `downloadImage(url)` - Download image to buffer
- `getMetafield(productId, namespace, key)` - Get metafield
- `setMetafield(productId, namespace, key, value)` - Set metafield

### MetafieldManager (src/metafields.js)

Manages metafield tracking:
- `getMetafield(productId)` - Retrieve tracking data
- `isHarmonized(productId)` - Check if processed
- `markAsHarmonized(productId, details)` - Mark complete
- `markAsInProgress(productId, details)` - Mark in progress
- `markAsFailed(productId, error, details)` - Mark failed
- `getProductsNeedingHarmonization(allProducts)` - Filter unprocessed
- `getStatistics(allProducts)` - Get processing stats

### ProductScaler (src/scaler.js)

Handles categorization and scaling logic:
- `categorizeProduct(width, height, title, type)` - Determine category
- `calculateScaledDimensions(width, height, category)` - Calculate scaled size
- `getScalingInfo(width, height, title, type)` - Complete scaling info
- `getCenterPosition(scaledWidth, scaledHeight)` - Get center coordinates
- `getShadowPosition(scaledWidth, scaledHeight)` - Get shadow position

### ImageProcessor (src/imageProcessor.js)

Performs image processing with Sharp:
- `processImage(buffer, productInfo)` - Main processing pipeline
- `removeBackground(buffer)` - Background removal
- `createContactShadow(width, height)` - Generate shadow SVG
- `processAndSave(inputPath, outputPath, productInfo)` - Local testing

### ShopifyImageAutomation (src/main.js)

Main orchestrator:
- `run(options)` - Main entry point
- `processProduct(product)` - Process single product
- `processBatch(products)` - Batch processing with concurrency

## Processing Pipeline

1. **Fetch Products**: Get all products from Shopify with pagination
2. **Filter**: Identify products needing harmonization (check metafields)
3. **Download**: Download original product images
4. **Categorize**: Determine category based on dimensions and metadata
5. **Process**:
   - Remove background (preserve alpha channel)
   - Scale according to category rules
   - Create canvas with #f3f3f4 background
   - Generate contact shadow
   - Composite layers
   - Export as WebP
6. **Upload**: Upload processed image to Shopify (if not dry run)
7. **Cleanup**: Delete old image
8. **Track**: Update metafield with processing status

## Quality Verification

Before running in production:

1. **Run Test Suite**:
   ```bash
   npm test
   ```

2. **Review comparison.html**:
   - Check shadow placement and opacity
   - Verify scaling per category
   - Confirm background color match
   - Test transparency (dripper test)

3. **Complete CHECKLIST.md**:
   - Follow verification steps
   - Document any issues

4. **Run Dry Run**:
   ```bash
   npm start -- --limit 10
   ```

5. **Test Limited Production**:
   ```bash
   # Set DRY_RUN=false
   npm start -- --limit 10
   ```

6. **Verify in Shopify Admin**:
   - Check processed products
   - Confirm image quality
   - Verify metafields

7. **Full Production Run**:
   ```bash
   npm start
   ```

## Command Line Options

```bash
# Limit processing to N products
npm start -- --limit 10
npm start -- -l 10

# Run test suite
npm test
```

## Error Handling

The system includes comprehensive error handling:

- **Product Level**: Failed products are marked with error status in metafields
- **Image Level**: Individual image failures don't stop product processing
- **Batch Level**: Process continues even if some products fail
- **Statistics**: Final report shows success/failure counts

## Rate Limiting

The system respects Shopify API rate limits:

- 500ms delay between product fetches
- 100ms delay between metafield checks
- 1000ms delay between processing batches
- Configurable concurrent processing limit

## Troubleshooting

### Common Issues

**"SHOPIFY_STORE_URL is required"**
- Ensure `.env` file exists and contains required variables
- Check `.env` is in the project root directory

**"Error fetching products"**
- Verify Shopify access token is valid
- Check token has required permissions (read_products, write_products, read_product_listings, write_product_listings)
- Ensure store URL is correct format (your-store.myshopify.com)

**"Background removal not working"**
- Ensure first run has internet access to download AI model (~50MB)
- Model is cached in ~/.cache/background-removal/ for future use
- Check ENABLE_BACKGROUND_REMOVAL=true in .env
- Review console logs for specific error messages
- AI model may struggle with very complex backgrounds - manual review recommended

**"Images look wrong in comparison.html"**
- Check canvas dimensions match specifications
- Verify background color is exactly #f3f3f4
- Review scaling logic for edge cases

**"Metafields not saving"**
- Verify token has metafield permissions
- Check Shopify metafield definitions exist
- Review API error messages in console

### Debug Mode

Enable verbose logging by checking console output. Each processing step logs progress and any issues encountered.

## Development

### Adding New Features

The modular architecture makes it easy to extend:

- **New scaling rules**: Modify `src/scaler.js`
- **Different shadow styles**: Update `src/imageProcessor.js`
- **Additional tracking**: Extend `src/metafields.js`
- **New API methods**: Add to `src/shopify.js`

### Testing Changes

Always test changes with:
1. `npm test` for visual verification
2. Dry run mode for safety
3. Limited production test (--limit 10)

## Important Notes

- **Use metafields, NOT tags** - Metafields provide structured data tracking
- **Preserve alpha channel** - Essential for products with holes/transparency
- **Shadow at base only** - Not behind entire product
- **Exact color match** - #f3f3f4 must be precise
- **WebP format** - For optimal file size and quality
- **Respect rate limits** - Batch processing includes delays
- **Idempotent processing** - Metafields prevent reprocessing

## Success Criteria

- ✅ All product images have consistent 2000×2500px canvas
- ✅ Background color exactly matches #f3f3f4
- ✅ Contact shadows properly placed at product base
- ✅ Correct scaling applied based on category
- ✅ Transparency preserved through product holes
- ✅ Metafield tracking shows completed status
- ✅ Test suite generates comparison.html successfully
- ✅ Dry run completes without errors
- ✅ Production run uploads to Shopify successfully

## Support

For issues, questions, or contributions:
- Review CHECKLIST.md for quality verification steps
- Check existing issues on GitHub
- Create new issue with details and logs

## License

MIT License - See LICENSE file for details

## Credits

Built for Another Corner
Powered by Sharp image processing library