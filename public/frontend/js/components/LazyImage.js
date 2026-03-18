/**
 * LazyImage Component - Mobile-Optimized
 * Progressive image loading with responsive srcset and Intersection Observer
 */

/**
 * @typedef {Object} LazyImageOptions
 * @property {string} src - Main image source
 * @property {string} alt - Alt text (required for accessibility)
 * @property {string} srcset - Responsive srcset (optional)
 * @property {string} sizes - Sizes attribute (optional)
 * @property {string} placeholder - Placeholder image (low-res, base64, or URL)
 * @property {string} className - CSS class names
 * @property {number} threshold - Intersection Observer threshold (0-1)
 * @property {string} rootMargin - Intersection Observer root margin
 * @property {boolean} eager - Load immediately without lazy loading
 * @property {Function} onLoad - Callback when image loads
 * @property {Function} onError - Callback when image fails to load
 */

export class LazyImage {
  /**
   * Create a lazy-loaded image
   * @param {LazyImageOptions} options - Image configuration
   */
  constructor(options = {}) {
    if (!options.src) {
      throw new Error('LazyImage requires a src option');
    }

    if (!options.alt) {
      console.warn('LazyImage: Missing alt text for accessibility');
    }

    this.options = {
      src: options.src,
      alt: options.alt || '',
      srcset: options.srcset || '',
      sizes: options.sizes || '',
      placeholder: options.placeholder || '',
      className: options.className || '',
      threshold: options.threshold || 0.1,
      rootMargin: options.rootMargin || '50px',
      eager: options.eager || false,
      onLoad: options.onLoad || null,
      onError: options.onError || null
    };

    this.element = null;
    this.observer = null;
    this.isLoaded = false;
  }

  /**
   * Create and return the image element
   * @returns {HTMLElement}
   */
  create() {
    this.element = document.createElement('img');
    this.element.className = `lazy-image ${this.options.className}`.trim();
    this.element.alt = this.options.alt;

    // ARIA attributes
    this.element.setAttribute('role', 'img');
    this.element.setAttribute('loading', this.options.eager ? 'eager' : 'lazy');

    // Set placeholder if provided
    if (this.options.placeholder) {
      this.element.src = this.options.placeholder;
      this.element.classList.add('lazy-image--placeholder');
    } else {
      // Use a 1x1 transparent pixel as placeholder
      this.element.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"%3E%3C/svg%3E';
    }

    // Store actual image URL in data attributes
    this.element.dataset.src = this.options.src;
    if (this.options.srcset) {
      this.element.dataset.srcset = this.options.srcset;
    }
    if (this.options.sizes) {
      this.element.dataset.sizes = this.options.sizes;
    }

    // Load eagerly if specified
    if (this.options.eager) {
      this._loadImage();
    } else {
      // Setup Intersection Observer
      this._setupObserver();
    }

    return this.element;
  }

  /**
   * Setup Intersection Observer for lazy loading
   * @private
   */
  _setupObserver() {
    // Check if Intersection Observer is supported
    if (!('IntersectionObserver' in window)) {
      // Fallback: load immediately
      this._loadImage();
      return;
    }

    // Create observer
    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            this._loadImage();
            this.observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: this.options.threshold,
        rootMargin: this.options.rootMargin
      }
    );

    // Start observing
    this.observer.observe(this.element);
  }

  /**
   * Load the actual image
   * @private
   */
  _loadImage() {
    if (this.isLoaded) return;

    const src = this.element.dataset.src;
    const srcset = this.element.dataset.srcset;
    const sizes = this.element.dataset.sizes;

    // Create a new image to preload
    const img = new Image();

    img.onload = () => {
      this._onImageLoad(src, srcset, sizes);
    };

    img.onerror = () => {
      this._onImageError();
    };

    // Start loading
    if (srcset) {
      img.srcset = srcset;
    }
    if (sizes) {
      img.sizes = sizes;
    }
    img.src = src;
  }

  /**
   * Handle successful image load
   * @private
   */
  _onImageLoad(src, srcset, sizes) {
    // Apply the loaded image to the element
    this.element.src = src;
    if (srcset) {
      this.element.srcset = srcset;
    }
    if (sizes) {
      this.element.sizes = sizes;
    }

    // Update state
    this.isLoaded = true;
    this.element.classList.remove('lazy-image--placeholder');
    this.element.classList.add('lazy-image--loaded');

    // Remove data attributes (no longer needed)
    delete this.element.dataset.src;
    delete this.element.dataset.srcset;
    delete this.element.dataset.sizes;

    // Callback
    if (this.options.onLoad) {
      this.options.onLoad(this.element);
    }

    // Dispatch custom event
    this.element.dispatchEvent(new CustomEvent('lazyload', { detail: { src } }));
  }

  /**
   * Handle image load error
   * @private
   */
  _onImageError() {
    this.element.classList.add('lazy-image--error');

    // Set a fallback error image (optional)
    this.element.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Crect fill="%23f0f0f0" width="100" height="100"/%3E%3Ctext x="50" y="50" text-anchor="middle" fill="%23999" font-size="12"%3EImage Error%3C/text%3E%3C/svg%3E';

    // Callback
    if (this.options.onError) {
      this.options.onError(this.element);
    }

    // Dispatch custom event
    this.element.dispatchEvent(new CustomEvent('lazyerror'));
  }

  /**
   * Manually trigger image load (useful for programmatic control)
   */
  load() {
    if (this.observer) {
      this.observer.unobserve(this.element);
      this.observer = null;
    }
    this._loadImage();
  }

  /**
   * Cleanup (remove observer)
   */
  destroy() {
    if (this.observer) {
      this.observer.unobserve(this.element);
      this.observer = null;
    }
  }
}

/**
 * Utility: Convert image URL to responsive srcset
 * @param {string} baseUrl - Base image URL (e.g., https://example.com/image.jpg)
 * @param {Array<number>} widths - Array of widths (e.g., [320, 640, 1024])
 * @returns {string} srcset string
 */
export function generateSrcset(baseUrl, widths = [320, 640, 1024, 1920]) {
  // Check if baseUrl has a query string
  const separator = baseUrl.includes('?') ? '&' : '?';

  return widths
    .map((width) => `${baseUrl}${separator}w=${width} ${width}w`)
    .join(', ');
}

/**
 * Utility: Generate sizes attribute based on breakpoints
 * @param {Object} breakpoints - Breakpoints object (e.g., { sm: '100vw', md: '50vw', lg: '33vw' })
 * @returns {string} sizes string
 */
export function generateSizes(breakpoints = {}) {
  const defaultBreakpoints = {
    sm: '(max-width: 640px) 100vw',
    md: '(max-width: 1024px) 50vw',
    default: '33vw'
  };

  const merged = { ...defaultBreakpoints, ...breakpoints };
  const sizes = [];

  Object.keys(merged).forEach((key) => {
    if (key !== 'default') {
      sizes.push(merged[key]);
    }
  });

  sizes.push(merged.default);
  return sizes.join(', ');
}

/**
 * Utility: Initialize lazy loading for existing images in DOM
 * @param {string} selector - CSS selector for images (default: 'img[data-src]')
 */
export function initLazyImages(selector = 'img[data-src]') {
  const images = document.querySelectorAll(selector);

  images.forEach((img) => {
    const lazyImage = new LazyImage({
      src: img.dataset.src,
      srcset: img.dataset.srcset || '',
      sizes: img.dataset.sizes || '',
      alt: img.alt,
      placeholder: img.src,
      className: img.className,
      eager: img.loading === 'eager'
    });

    // Replace the existing image with the lazy-loaded one
    const newImg = lazyImage.create();
    img.parentNode.replaceChild(newImg, img);
  });
}

/**
 * Utility: Preload critical images (above-the-fold)
 * @param {Array<string>} urls - Array of image URLs to preload
 */
export function preloadImages(urls = []) {
  urls.forEach((url) => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.as = 'image';
    link.href = url;
    document.head.appendChild(link);
  });
}

/**
 * Utility: Get optimal image size based on device
 * @param {number} originalWidth - Original image width
 * @returns {number} Optimal width for current device
 */
export function getOptimalImageSize(originalWidth) {
  const dpr = window.devicePixelRatio || 1;
  const viewportWidth = window.innerWidth;

  // Calculate optimal width considering device pixel ratio
  const optimalWidth = viewportWidth * dpr;

  // Common sizes for responsive images
  const sizes = [320, 640, 768, 1024, 1280, 1920, 2560];

  // Find the smallest size that's larger than optimal
  const selectedSize = sizes.find((size) => size >= optimalWidth) || sizes[sizes.length - 1];

  // Don't upscale beyond original width
  return Math.min(selectedSize, originalWidth);
}

/**
 * Utility: Create a blur-up placeholder from image
 * @param {string} imageUrl - Image URL
 * @param {number} width - Placeholder width (default: 40px)
 * @returns {Promise<string>} Base64 encoded placeholder
 */
export async function createBlurPlaceholder(imageUrl, width = 40) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      // Calculate dimensions maintaining aspect ratio
      const aspectRatio = img.height / img.width;
      canvas.width = width;
      canvas.height = width * aspectRatio;

      // Draw scaled-down image
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Apply blur effect
      ctx.filter = 'blur(10px)';
      ctx.drawImage(canvas, 0, 0, canvas.width, canvas.height);

      // Convert to base64
      const placeholder = canvas.toDataURL('image/jpeg', 0.5);
      resolve(placeholder);
    };

    img.onerror = () => {
      reject(new Error('Failed to create blur placeholder'));
    };

    img.src = imageUrl;
  });
}

// Export for use in other modules
export default LazyImage;
