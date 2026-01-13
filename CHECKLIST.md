# Quality Verification Checklist

Use this checklist to verify the quality of processed product images before running in production.

## Visual Quality Checks

### Shadow Placement
- [ ] Shadow is grounded to the base of the product
- [ ] Shadow is not behind the entire product
- [ ] Shadow appears as a contact shadow (elliptical shape)
- [ ] Shadow has proper Gaussian blur applied
- [ ] Shadow opacity is 18% (rgba(0, 0, 0, 0.18))
- [ ] Shadow is proportional to product width

### Scaling & Sizing
- [ ] Tall/Thin products (aspect ratio < 0.5) scaled to 85% of canvas height
- [ ] Wide products (aspect ratio > 1.5) scaled to 82% of canvas width
- [ ] Small/Accessory products scaled to 50% of canvas height
- [ ] Default products scaled to 82% of longest side
- [ ] Products are properly centered on canvas
- [ ] No products are cut off or exceed canvas boundaries

### Background & Transparency
- [ ] Background removal is clean (no artifacts)
- [ ] Transparency preserved through product "holes" (dripper test)
- [ ] Background color is exactly #f3f3f4
- [ ] Background matches site whitespace color
- [ ] No white halos around product edges
- [ ] Alpha channel properly maintained

### Canvas & Format
- [ ] Canvas dimensions are exactly 2000×2500 px
- [ ] Output format is WebP
- [ ] WebP quality is 90%
- [ ] File sizes are optimized (reasonable compression)
- [ ] Images maintain visual quality after compression

## Category Testing

Test each category with at least one example:

### Tall/Thin Products
- [ ] Example found and processed
- [ ] Scaled to 85% of canvas height
- [ ] Aspect ratio correctly detected (< 0.5)
- [ ] Shadow positioned correctly
- [ ] Product centered properly

### Wide Products
- [ ] Example found and processed
- [ ] Scaled to 82% of canvas width
- [ ] Aspect ratio correctly detected (> 1.5)
- [ ] Shadow positioned correctly
- [ ] Product centered properly

### Small/Accessory Products
- [ ] Example found and processed
- [ ] Scaled to 50% of canvas height
- [ ] Detected by size (< 500px) OR keyword match
- [ ] Shadow positioned correctly
- [ ] Product centered properly

### Default Products
- [ ] Example found and processed
- [ ] Scaled to 82% of longest side
- [ ] Standard aspect ratio (0.5 - 1.5)
- [ ] Shadow positioned correctly
- [ ] Product centered properly

## Technical Verification

### Metafield Tracking
- [ ] Metafield namespace is `automation`
- [ ] Metafield key is `harmonized`
- [ ] Metafield contains proper JSON structure
- [ ] Status values are correct (completed, in_progress, failed)
- [ ] Timestamps are recorded
- [ ] Product titles are stored
- [ ] Processed images array is populated
- [ ] Category information is saved

### API Integration
- [ ] Shopify API authentication works
- [ ] Product fetching with pagination works
- [ ] Image download successful
- [ ] Image upload successful
- [ ] Old images properly deleted
- [ ] Metafield read/write operations work
- [ ] Rate limiting respected

### Error Handling
- [ ] Products without images are skipped gracefully
- [ ] Failed products are marked with error status
- [ ] Error messages are descriptive
- [ ] Stack traces captured for debugging
- [ ] Process continues after individual failures
- [ ] Statistics show failed product count

## Testing Suite

### Test Run (test_run.js)
- [ ] `npm test` executes successfully
- [ ] Finds at least one example of each category
- [ ] Downloads images correctly
- [ ] Processes images locally
- [ ] Saves original and processed images to output/
- [ ] Generates comparison.html
- [ ] HTML opens in browser
- [ ] Side-by-side comparison is clear
- [ ] Metadata is displayed correctly

### Comparison HTML
- [ ] All category examples are shown
- [ ] Original vs processed images displayed
- [ ] Dimensions are listed
- [ ] Category badges are correct
- [ ] Scaling information is accurate
- [ ] Interactive checklist is present
- [ ] Background color preview works

## Pre-Production Verification

Before running in production mode (DRY_RUN=false):

### Dry Run Testing
- [ ] Run `npm start` with DRY_RUN=true
- [ ] Process completes without errors
- [ ] Review console output for warnings
- [ ] Check metafield updates (should show "would upload")
- [ ] Verify rate limiting delays are working

### Limited Production Test
- [ ] Run with `--limit 10` flag
- [ ] Verify 10 products process successfully
- [ ] Check products in Shopify admin
- [ ] Verify images uploaded correctly
- [ ] Verify old images deleted
- [ ] Confirm metafields set properly
- [ ] Review processed images visually

### Final Checks
- [ ] All checklist items above are complete
- [ ] comparison.html reviewed and approved
- [ ] Test products look correct in Shopify
- [ ] No duplicate images on products
- [ ] Metafields tracking correctly
- [ ] Statistics reporting accurately
- [ ] Ready for full production run

## Post-Production Monitoring

After running in production:

- [ ] Check statistics output
- [ ] Review failed products list
- [ ] Spot-check random products visually
- [ ] Verify metafield data integrity
- [ ] Confirm no duplicate images
- [ ] Check file sizes are reasonable
- [ ] Monitor Shopify admin for any issues
- [ ] Document any problems encountered
- [ ] Update checklist with learnings

## Special Cases to Test

### Transparency Test (Dripper Test)
- [ ] Find product with holes/transparency (e.g., coffee dripper)
- [ ] Process the image
- [ ] Verify background visible through holes
- [ ] Confirm no white fill in transparent areas
- [ ] Check alpha channel preserved

### Keywords Test
- [ ] Test small accessory keywords: pin, badge, sticker, card
- [ ] Test small accessory keywords: bookmark, keychain, magnet
- [ ] Test small accessory keywords: patch, button
- [ ] Verify products with keywords are categorized as small_accessory
- [ ] Verify 50% scaling applied

### Edge Cases
- [ ] Very small images (< 200px)
- [ ] Very large images (> 5000px)
- [ ] Square images (aspect ratio = 1.0)
- [ ] Nearly square images (aspect ratio 0.9-1.1)
- [ ] Products with multiple images
- [ ] Products without product_type
- [ ] Products with special characters in title

## Notes

- Use this checklist for every test run
- Document any issues found
- Update checklist based on findings
- Keep comparison.html for reference
- Review with team before production
