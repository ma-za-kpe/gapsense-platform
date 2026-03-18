# GapSense Frontend - Mobile-First Architecture

## 📁 Directory Structure

```
frontend/
├── static/           # Static HTML files (entry points)
├── css/             # Stylesheets (mobile-first)
│   ├── base/        # Reset, variables, typography
│   ├── components/  # Component-specific styles
│   ├── layouts/     # Grid systems, containers
│   └── mobile/      # Mobile-specific overrides
├── js/              # JavaScript modules
│   ├── modules/     # Feature modules (api, state, ui)
│   └── utils/       # Utility functions
├── components/      # Reusable UI components
├── assets/          # Images, icons, fonts
│   ├── images/      # Exercise book images
│   └── icons/       # SVG icons
├── config/          # Configuration files
└── types/           # TypeScript type definitions
```

## 🎯 Mobile-First Principles

### 1. **Responsive Breakpoints**
```css
/* Mobile first - start with base mobile styles */
.component { /* 320px+ */ }

@media (min-width: 768px) { /* Tablets */ }
@media (min-width: 1024px) { /* Desktop */ }
@media (min-width: 1440px) { /* Large desktop */ }
```

### 2. **Touch Targets**
- Minimum touch target: **44x44px** (Apple HIG)
- Minimum spacing: **8px** between interactive elements
- Large, thumb-friendly buttons for mobile

### 3. **Performance Budget**
- Initial bundle: **< 200KB** (gzipped)
- First Contentful Paint: **< 1.5s** on 3G
- Time to Interactive: **< 3.5s** on 3G
- Images: WebP with fallback, lazy loading

### 4. **Offline-First**
- Service Worker for core functionality
- IndexedDB for local data storage
- Progressive Web App (PWA) manifest

### 5. **Accessibility**
- WCAG 2.1 AA compliance
- Semantic HTML5
- ARIA labels for screen readers
- Keyboard navigation support

## 🚀 Getting Started

### Development
```bash
npm install
npm run dev        # Start Vite dev server
npm run build      # Build for production
npm run preview    # Preview production build
```

### Testing
```bash
npm run test              # Run unit tests
npm run test:mobile       # Run mobile breakpoint tests
npm run test:a11y         # Run accessibility tests
npm run lighthouse        # Run Lighthouse audit
```

## 📱 Mobile Optimization Checklist

- [ ] Viewport meta tag configured
- [ ] Touch event handlers added
- [ ] Responsive images with srcset
- [ ] Lazy loading implemented
- [ ] Service Worker registered
- [ ] PWA manifest created
- [ ] Hamburger menu for mobile
- [ ] Virtual scrolling for long lists
- [ ] Code splitting configured
- [ ] Bundle size optimized
- [ ] Lighthouse score > 90

## 🔧 Build Tools

- **Vite**: Fast build tool with HMR
- **TypeScript**: Type safety
- **PostCSS**: CSS processing
- **Playwright**: E2E testing
- **Lighthouse CI**: Performance monitoring

## 📊 Current Status

**Phase**: Foundation & Mobile Audit
**Next**: Extract CSS from demo.html with mobile-first approach
