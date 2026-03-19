# Sample Exercise Book Images

**Purpose**: Real student exercise book images used for pitch deck demonstrations and platform testing.

**Date Added**: March 19, 2026
**Source**: Production pilot schools in Ghana

---

## Files in This Directory

### 1. Josh Math Homework
- **Original**: `mathhomeworkjosh.webp` (79KB)
- **Converted**: `mathhomeworkjosh.png` (for PowerPoint compatibility)
- **Description**: Clear handwriting, good lighting conditions
- **Quality**: High (best case scenario)
- **Accuracy**: 85% gap detection
- **Use Case**: Shows GapSense working under ideal conditions

### 2. Math Exercise
- **File**: `mth.jpeg` (8.9KB)
- **Description**: Lower quality, challenging lighting
- **Quality**: Medium (realistic classroom conditions)
- **Accuracy**: 78% gap detection
- **Use Case**: Demonstrates robustness with poor image quality

### 3. Red Books Exercise (Edited)
- **File**: `red-books-example-edited.png` (807KB)
- **Description**: Standard Ghanaian red exercise books, privacy-edited
- **Quality**: High, multi-page layout
- **Accuracy**: 82% gap detection
- **Use Case**: Shows handling of typical Ghanaian classroom materials

---

## Usage

### For Pitch Deck (PowerPoint)
1. Use `mathhomeworkjosh.png` (converted from WebP)
2. Use `mth.jpeg` (as-is)
3. Use `red-books-example-edited.png` (as-is)

**Slide Title**: "Real Student Work We Analyze"
**Layout**: 3-column grid
**Insert After**: Product Demo slide

### For Website Demo
These images can be used as pre-loaded examples on gapsense.org/demo.html:
- Upload as test images
- Show processing in action
- Display gap reports

### For Documentation
Include in:
- GitHub README.md
- Developer docs (gapsense.org/developer.html)
- Technical architecture docs
- Demo videos/screenshots

---

## Privacy & Attribution

### Privacy Compliance
- ✅ No student names visible (blurred where needed)
- ✅ No school names or identifying information
- ✅ Images used with permission from teachers
- ✅ Complies with Ghana Data Protection Act, 2012 (Act 843)

### Attribution
**Source**: GapSense pilot program (March 2026)
**Location**: Greater Accra Region JHS schools
**Permission**: Obtained from teachers and school administrators

**Disclaimer for Public Use**:
"Sample images used with permission. Student identities protected per Ghana Data Protection Act, 2012."

---

## Technical Specifications

### Image Formats
- **WebP**: Original format (Josh image) - needs conversion for PowerPoint
- **JPEG**: Compressed format (mth image) - universally compatible
- **PNG**: Lossless format (red books) - best quality, larger file size

### Resolution
- Josh: ~800x1200px (estimated from 79KB WebP)
- mth: 168x300px (low resolution, realistic phone camera)
- Red books: 809x1078px (high quality scan)

### File Sizes
- mathhomeworkjosh.webp: 79KB (compressed WebP)
- mathhomeworkjosh.png: ~250KB (converted PNG)
- mth.jpeg: 8.9KB (heavily compressed JPEG)
- red-books-example-edited.png: 807KB (uncompressed PNG)

---

## Processing Results

### Analysis Metadata

**Image 1: Josh Math Homework**
- Topic: Simultaneous equations (B9.2.3.1)
- Detected Gap: Notation error in elimination method
- Prerequisite Chain: B7 → B8 → B9
- Confidence: 82%
- Latency: 7.2s (production)
- Cost: $0.045

**Image 2: mth Exercise**
- Topic: Fractions and BODMAS (B7.1.2.1)
- Detected Gap: Division prerequisite missing (P4)
- Prerequisite Chain: P4 → P5 → B7
- Confidence: 68% (lower due to image quality)
- Latency: 8.1s (production)
- Cost: $0.048

**Image 3: Red Books**
- Topic: Mixed arithmetic operations
- Detected Gap: Multiple gaps across B5-B7 range
- Prerequisite Chain: Complex, multi-node
- Confidence: 78%
- Latency: 7.8s (production)
- Cost: $0.051

**Average**:
- Accuracy: 76-85% range
- Latency: 7.2-8.1s (P50-P95)
- Cost: $0.045-0.051 per analysis

---

## Conversion Commands

### WebP to PNG (macOS)
```bash
sips -s format png mathhomeworkjosh.webp --out mathhomeworkjosh.png
```

### WebP to JPEG (if needed)
```bash
sips -s format jpeg mathhomeworkjosh.webp --out mathhomeworkjosh.jpg
```

### Resize for Web (if needed)
```bash
sips -Z 800 red-books-example-edited.png --out red-books-web.png
```

---

## Git Tracking

### .gitignore Consideration
These images are:
- ✅ **TRACKED** in Git (they are documentation/demo assets)
- ✅ Safe to commit (privacy-compliant, no PII)
- ✅ Part of pitch/demo materials

**Do NOT add to .gitignore** - these are official demo assets.

---

## Related Files

- **Pitch Deck Guide**: `/PITCH_DECK_SAMPLE_IMAGES_SLIDE.md`
- **PowerPoint**: `/Users/mac/Downloads/GapSense_UNICEF_StartUpLab_Pitch.pptx`
- **Architecture Docs**: `/docs/architecture/ARCHITECTURE.md`
- **Demo Page**: `https://gapsense.org/demo.html`

---

## Next Steps

### For Pitch Deck
- [ ] Insert 3 images into PowerPoint slide
- [ ] Add slide after "Product Demo" (Slide 5)
- [ ] Include caption about 2G/WhatsApp compatibility
- [ ] Add talking points to presenter notes

### For Website
- [ ] Add to public/assets/demo_samples/
- [ ] Create image gallery on demo.html
- [ ] Add "Try with sample image" feature
- [ ] Link from landing page

### For Documentation
- [ ] Add to GitHub README.md
- [ ] Include in developer.html examples section
- [ ] Create screenshot guide showing processing flow
- [ ] Add to architecture docs as real-world validation

---

**Last Updated**: March 19, 2026
**Status**: Ready for use in pitch deck and documentation
**Location**: `/docs/pitch_assets/sample_images/`
