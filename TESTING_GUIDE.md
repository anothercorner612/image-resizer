# Complete Testing Guide

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Node.js 18+ installed (`node --version`)
- [ ] Python 3.6+ installed (`python3 --version`)
- [ ] npm installed (`npm --version`)
- [ ] Git repository cloned
- [ ] Internet connection (for first run model download)
- [ ] ~500MB free disk space (for models)
- [ ] Shopify Admin API access token with permissions:
  - read_products
  - write_products
  - read_product_listings
  - write_product_listings

---

## Phase 1: Initial Setup (5 minutes)

### 1.1 Install Node.js Dependencies

```bash
cd /path/to/image-resizer
npm install
```

**Expected Output:**
- Should install @shopify/shopify-api, sharp, dotenv, axios
- No errors about missing packages

### 1.2 Install Python Dependencies

```bash
pip3 install withoutbg numpy scipy pillow
```

**Expected Output:**
```
Successfully installed withoutbg-X.X.X numpy-X.X.X scipy-X.X.X pillow-X.X.X
```

**Note:** This may take 2-3 minutes to compile native extensions.

### 1.3 Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required - Replace with your actual values
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Canvas Configuration (default values)
CANVAS_WIDTH=2000
CANVAS_HEIGHT=2500

# Visual Settings
BACKGROUND_COLOR=#f3f3f4
SHADOW_OPACITY=0.18
WEBP_QUALITY=90

# Processing Configuration
DRY_RUN=true                    # ✅ Keep as 'true' for testing
MAX_CONCURRENT_PROCESSES=5

# Image Processing Options
ENABLE_AUTO_TRIM=true
ENABLE_BACKGROUND_REMOVAL=true
```

**Critical:** Keep `DRY_RUN=true` for all testing phases.

---

## Phase 2: Python Integration Test (3-5 minutes first run)

### 2.1 Test withoutbg Integration

```bash
node test_withoutbg.js
```

**What This Tests:**
- Python subprocess execution
- withoutbg model download and initialization
- Alpha channel processing
- Buffer conversion

**Expected Output (First Run):**
```
=== Testing withoutbg Background Removal ===

1. Creating test image...
✓ Test image created (500×500 with orange square)

2. Testing background removal...
   This will download ~320MB models on first run
   Please be patient...

Initializing withoutBG opensource model...
Downloading models from HuggingFace...
[Progress bars for model download]

Processing: /path/to/temp/input_xxx.png
Success: /path/to/temp/output_xxx.png

3. Background removal completed in 45.3s
   ✓ Output: 500×500
   ✓ Format: png
   ✓ Has alpha: true
   ✓ Buffer size: 123.4KB

✅ TEST PASSED - withoutbg is working!
```

**First Run Timing:**
- ~30-60 seconds for model download (one-time)
- Models cached in `~/.cache/huggingface/`

**Subsequent Runs:**
```bash
node test_withoutbg.js
```
Should complete in 2-3 seconds.

**Troubleshooting:**
- **"python3: command not found"** → Install Python 3
- **"No module named 'withoutbg'"** → Run `pip3 install withoutbg`
- **Network errors** → Check internet connection for model download
- **Permission denied** → Run `chmod +x remove_bg.py`

---

## Phase 3: Category Testing (5-10 minutes)

### 3.1 Run Test Suite

```bash
npm test
```

**What This Tests:**
- Shopify API connection
- Product fetching and pagination
- Category detection (tall/thin, wide, small/accessory, default)
- Complete image processing pipeline
- Background removal on real products
- Shadow generation
- Canvas compositing
- WebP export

**Expected Output:**
```
🔍 Finding example products for each category...

📦 Fetching products from Shopify...
✓ Found 247 products

🔍 Searching for category examples...
  ✓ Found tall/thin example: "Coffee Dripper" (aspect ratio: 0.45)
  ✓ Found wide example: "Desk Mat" (aspect ratio: 2.1)
  ✓ Found small/accessory example: "Enamel Pin" (512px, keyword match)
  ✓ Found default example: "Coffee Mug" (aspect ratio: 0.85)

🎨 Processing examples...

[1/4] Processing: Coffee Dripper (tall/thin)
  → Downloading image...
  → Removing background with withoutbg (Python)...
  → Smart trimming (colorful product, threshold: 15)...
  → Scaling to 85% of canvas height...
  → Creating contact shadow...
  → Compositing to canvas...
  → Exporting as WebP...
  ✓ Completed in 3.2s

[2/4] Processing: Desk Mat (wide)
  → Downloading image...
  → Removing background with withoutbg (Python)...
  → Smart trimming (colorful product, threshold: 15)...
  → Scaling to 82% of canvas width...
  → Creating contact shadow...
  → Compositing to canvas...
  → Exporting as WebP...
  ✓ Completed in 2.8s

[3/4] Processing: Enamel Pin (small_accessory)
  → Downloading image...
  → Removing background with withoutbg (Python)...
  → Smart trimming (colorful product, threshold: 15)...
  → Scaling to 50% of canvas height...
  → Creating contact shadow...
  → Compositing to canvas...
  → Exporting as WebP...
  ✓ Completed in 2.1s

[4/4] Processing: Coffee Mug (default)
  → Downloading image...
  → Removing background with withoutbg (Python)...
  → Smart trimming (white product, threshold: 5)...
  → Scaling to 82% of longest side...
  → Creating contact shadow...
  → Compositing to canvas...
  → Exporting as WebP...
  ✓ Completed in 2.5s

📊 Results saved to:
  → output/original/ (4 original images)
  → output/processed/ (4 processed images)
  → comparison.html

✅ Open comparison.html in your browser to review results
```

### 3.2 Visual Quality Review

```bash
open comparison.html
# or
xdg-open comparison.html  # Linux
# or manually open in browser
```

**Check the following for each image:**

#### ✅ Background Quality
- [ ] Background is solid #f3f3f4 color
- [ ] No white halos around product edges
- [ ] No remnants of original background
- [ ] Clean edges on colorful products (greeting cards, calendars)
- [ ] White products preserved (white books, white mugs)

#### ✅ Shadow Quality
- [ ] Shadow is positioned at product base
- [ ] Shadow is NOT behind entire product
- [ ] Shadow has elliptical/contact shape
- [ ] Shadow opacity looks correct (~18%)
- [ ] Shadow is proportional to product width

#### ✅ Scaling & Positioning
- [ ] Products are centered on canvas
- [ ] Tall/thin products scaled to 85% height
- [ ] Wide products scaled to 82% width
- [ ] Small accessories scaled to 50% height
- [ ] Default products scaled to 82% of longest side
- [ ] No products cut off or extending beyond canvas

#### ✅ Transparency (Dripper Test)
- [ ] If product has holes (dripper, basket), background visible through them
- [ ] No white fill in transparent areas
- [ ] Alpha channel properly maintained

#### ✅ Technical Quality
- [ ] Canvas is 2000×2500px
- [ ] Format is WebP
- [ ] Images look sharp (no excessive blur)
- [ ] File sizes reasonable (50-200KB typical)

---

## Phase 4: Limited Dry Run (10-15 minutes)

### 4.1 Test on 10 Products

```bash
npm start -- --limit 10
```

**What This Tests:**
- Real product processing at scale
- Error handling
- Metafield tracking (simulated)
- Rate limiting
- Statistics reporting

**Expected Output:**
```
🚀 Starting Shopify Image Automation
📊 Configuration:
   • Canvas: 2000×2500px
   • Background: #f3f3f4
   • Shadow: 18% opacity
   • WebP Quality: 90%
   • Dry Run: true ✓
   • Background Removal: true ✓
   • Max Concurrent: 5

📦 Fetching products from Shopify...
✓ Found 247 products

🔍 Checking which products need harmonization...
  • Completed: 58
  • In Progress: 0
  • Failed: 3
  • Pending: 186
  • Skipped: 0

⚙️  Processing limit: 10 products
📋 Selected 10 products for processing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/10] Processing: Coffee Mug (ID: 123456789)
  ↓ Downloading image...
  ⚡ Removing background...
  ✂️  Trimming edges (white product, threshold: 5)...
  📏 Category: default (aspect ratio: 0.82)
  🔄 Scaling to 82% of longest side...
  🎨 Creating contact shadow...
  📐 Compositing to 2000×2500px canvas...
  💾 Exporting as WebP (90% quality)...
  ☁️  Would upload to Shopify (DRY_RUN)
  📝 Would update metafield (DRY_RUN)
  ✓ Completed in 2.8s

[2/10] Processing: Greeting Card Set (ID: 123456790)
  ↓ Downloading image...
  ⚡ Removing background...
  ✂️  Trimming edges (colorful product, threshold: 15)...
  📏 Category: default (aspect ratio: 1.0)
  🔄 Scaling to 82% of longest side...
  🎨 Creating contact shadow...
  📐 Compositing to 2000×2500px canvas...
  💾 Exporting as WebP (90% quality)...
  ☁️  Would upload to Shopify (DRY_RUN)
  📝 Would update metafield (DRY_RUN)
  ✓ Completed in 3.1s

[... 8 more products ...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Final Statistics:
   ✓ Successful: 10
   ✗ Failed: 0
   ⊘ Skipped: 0
   ⏱  Total Time: 29.4s
   📈 Average: 2.9s per product

✅ Automation completed successfully!
```

### 4.2 Review Output

Check the console logs for:
- [ ] No Python errors
- [ ] No "fallback to Sharp" messages (indicates Python working)
- [ ] Temp file cleanup working
- [ ] Processing times reasonable (2-4s per image)
- [ ] All products marked "Would upload" (dry run mode)

---

## Phase 5: Quality Checklist (10 minutes)

### 5.1 Complete CHECKLIST.md

Open and review `CHECKLIST.md`:

```bash
cat CHECKLIST.md
```

Go through each section and verify:
- [ ] Visual Quality Checks (shadows, scaling, background, transparency)
- [ ] Category Testing (all 4 categories tested)
- [ ] Technical Verification (metafields structure correct)

---

## Phase 6: Limited Production Test (10-15 minutes)

⚠️ **Warning:** This will upload to Shopify! Only proceed if dry run looked good.

### 6.1 Enable Production Mode

Edit `.env`:
```bash
DRY_RUN=false  # ⚠️ This enables real uploads
```

### 6.2 Run on 3 Test Products

```bash
npm start -- --limit 3
```

**What This Does:**
- Processes 3 real products
- Uploads processed images to Shopify
- Deletes old images
- Updates metafields

**Expected Output:**
```
🚀 Starting Shopify Image Automation
📊 Configuration:
   • Canvas: 2000×2500px
   • Background: #f3f3f4
   • Shadow: 18% opacity
   • WebP Quality: 90%
   • Dry Run: false ⚠️  PRODUCTION MODE
   • Background Removal: true ✓

[Processing output similar to dry run...]

[1/3] Processing: Test Product 1 (ID: 123456789)
  [... processing steps ...]
  ☁️  Uploading to Shopify...
  ✓ Image uploaded (new ID: 987654321)
  🗑️  Deleting old image (ID: 123456789)...
  ✓ Old image deleted
  📝 Updating metafield...
  ✓ Metafield updated (status: completed)
  ✓ Completed in 5.2s

[2/3] [...]
[3/3] [...]

📊 Final Statistics:
   ✓ Successful: 3
   ✗ Failed: 0
   ⊘ Skipped: 0
   ⏱  Total Time: 16.8s

✅ Automation completed successfully!
```

### 6.3 Verify in Shopify Admin

1. Go to Shopify Admin → Products
2. Find the 3 processed products
3. Check each product:
   - [ ] New image is 2000×2500px
   - [ ] Background is #f3f3f4
   - [ ] Shadow looks correct
   - [ ] Product is properly scaled
   - [ ] No white edge artifacts
   - [ ] Only 1 image per product (old deleted)

4. Check Metafields:
   - Go to Product → Metafields
   - Look for namespace: `automation`, key: `harmonized`
   - Verify JSON structure:
     ```json
     {
       "status": "completed",
       "processedAt": "2026-01-13T...",
       "productTitle": "Product Name",
       "category": "default",
       "scaledDimensions": {"width": 1640, "height": 2050}
     }
     ```

---

## Phase 7: Full Production Run (varies by product count)

### 7.1 Final Preparation

Before running on all products:
- [ ] All test phases completed successfully
- [ ] Visual quality verified
- [ ] Shopify uploads working
- [ ] Metafields tracking correctly
- [ ] No errors in logs
- [ ] `.env` has `DRY_RUN=false`

### 7.2 Run Full Automation

```bash
npm start
```

This will process ALL products that need harmonization.

**Monitoring:**
- Watch console output for errors
- Note processing times
- Check for any "failed" products
- Verify statistics at the end

**Expected Timeline:**
- 247 products × 3 seconds average = ~12 minutes total
- With concurrency (5 processes) = ~3-4 minutes

### 7.3 Post-Production Verification

After completion:

1. **Check Statistics:**
   ```
   📊 Final Statistics:
      ✓ Successful: 186
      ✗ Failed: 0
      ⊘ Skipped: 3
   ```

2. **Spot-Check Products:**
   - Review 10-15 random products in Shopify
   - Check different categories
   - Verify challenging products (multi-colored books, white products)

3. **Review Failed Products (if any):**
   - Check console logs for error messages
   - Use skip functionality if needed:
     ```bash
     npm run skip <product_id> "Reason for skipping"
     ```

---

## Troubleshooting Common Issues

### Issue: "Python background removal failed"

**Symptoms:**
```
Python background removal failed: Command failed: python3 ...
```

**Solutions:**
1. Check Python installed: `python3 --version`
2. Check withoutbg installed: `pip3 list | grep withoutbg`
3. Check permissions: `chmod +x remove_bg.py`
4. Test manually: `python3 remove_bg.py test_input.png test_output.png`

---

### Issue: "No products found needing harmonization"

**Symptoms:**
```
✓ Found 247 products
Pending: 0
```

**Reason:** All products already processed (have metafield with status "completed")

**Solutions:**
- This is expected if you've run before
- To reprocess, manually delete metafields in Shopify Admin
- Or process specific products by updating their metafield status

---

### Issue: White edges still visible on colorful products

**Symptoms:** Products like greeting cards still have white edges after processing

**Solutions:**
1. Check if background removal is enabled: `ENABLE_BACKGROUND_REMOVAL=true`
2. Verify Python subprocess working (not falling back to Sharp)
3. Check console logs for "Bold color detection" messages
4. May need to adjust saturation threshold in `remove_bg.py` (currently 40)

---

### Issue: White products getting cropped

**Symptoms:** White book covers or white mugs have edges cut off

**Reason:** Trim threshold too aggressive for white products

**Solutions:**
- Check color analysis working: Look for "white product, threshold: 5" in logs
- May need to adjust threshold in `imageProcessor.js` line 133
- Current: 5 for white, 15 for colorful

---

### Issue: Shadows floating or mispositioned

**Symptoms:** Shadow not touching product base

**Reason:** Using scaled dimensions instead of actual dimensions

**Check:**
- Verify shadow positioned using `actualWidth` and `actualHeight`
- Review `imageProcessor.js` lines 83-103

---

### Issue: Processing very slow (>10s per image)

**Possible Causes:**
1. **First run downloading models** - Normal, wait for completion
2. **Network issues** - Check internet connection
3. **Resource constraints** - Check CPU/memory usage
4. **Large images** - 4000px+ images take longer

**Solutions:**
- Reduce `MAX_CONCURRENT_PROCESSES` if system struggling
- Increase timeout if hitting 120s limit
- Check disk space for temp files

---

## GitHub Secrets Question

**Q: Should we use GitHub Secrets instead of .env file?**

**A: No, not for this use case.**

**Reasoning:**
- ✅ **Use .env file** because:
  - This is a server-side automation tool
  - Runs locally on your server/computer
  - Needs persistent credentials
  - Not running in GitHub Actions CI/CD

- ❌ **GitHub Secrets** are only for:
  - GitHub Actions workflows
  - CI/CD pipelines
  - Automated testing in GitHub infrastructure

**Keep using `.env` file with:**
- Add `.env` to `.gitignore` (already done ✓)
- Never commit `.env` to git (already protected ✓)
- Provide `.env.example` as template (already done ✓)

**Security Best Practices:**
- Keep `.env` file secure on your server
- Use restrictive file permissions: `chmod 600 .env`
- Rotate Shopify access tokens periodically
- Use scoped tokens (only required permissions)

---

## Summary Checklist

Before merging to main, verify:

- [ ] Phase 1: Environment setup completed
- [ ] Phase 2: Python integration test passed
- [ ] Phase 3: Category testing passed
- [ ] Phase 4: Limited dry run successful (10 products)
- [ ] Phase 5: Quality checklist completed
- [ ] Phase 6: Limited production test successful (3 products)
- [ ] Visual quality verified in Shopify Admin
- [ ] Metafields tracking correctly
- [ ] No errors in production logs
- [ ] Ready for Phase 7: Full production run

**When all checked:** ✅ Ready to merge to main!

---

**Questions or Issues?**
- Review console logs
- Check CHECKLIST.md
- Review REVIEW_REPORT.md for implementation details
