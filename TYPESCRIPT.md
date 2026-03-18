# TypeScript Configuration for GapSense

## Overview
This project uses TypeScript for type checking JavaScript files with strict mode enabled.

## Setup

### Install Dependencies
```bash
npm install
```

This installs TypeScript 5.3+ and type definitions for Node.js.

## Usage

### Type Check All Files
```bash
npm run type-check
```

### Watch Mode (Live Type Checking)
```bash
npm run type-check:watch
```

### Combined Linting (JS + CSS + TypeScript)
```bash
npm run lint
```

## Configuration

### tsconfig.json
- **Strict Mode**: Enabled for maximum type safety
- **allowJs**: Enables type checking for JavaScript files
- **checkJs**: Type checks JavaScript using JSDoc comments
- **Target**: ES2020 for modern browser support
- **Module**: ESNext for Vite bundler

### Type Checking JavaScript Files

Add JSDoc comments to your JavaScript files for type checking:

```javascript
/**
 * Upload an image to the server
 * @param {File} file - The image file to upload
 * @param {string} phoneNumber - Teacher's phone number
 * @returns {Promise<{success: boolean, report_id?: string, error?: string}>}
 */
async function uploadImage(file, phoneNumber) {
  // Implementation
}
```

### Type Definitions

```javascript
/**
 * @typedef {Object} StudentGap
 * @property {string} gap_node_id - Knowledge gap ID (e.g., "B6.1.2.1")
 * @property {string} description - Human-readable gap description
 * @property {number} confidence - Confidence score (0-1)
 * @property {string} severity - "high" | "medium" | "low"
 */

/**
 * @typedef {Object} AnalysisReport
 * @property {string} report_id - Unique report identifier
 * @property {StudentGap[]} gaps - Array of identified knowledge gaps
 * @property {number} confidence - Overall analysis confidence
 * @property {string} created_at - ISO 8601 timestamp
 */
```

## Benefits

1. **Type Safety**: Catch errors before runtime
2. **IntelliSense**: Better autocomplete in VS Code
3. **Documentation**: JSDoc serves as inline documentation
4. **Refactoring**: Safer code refactoring with type awareness
5. **Migration Path**: Easy gradual migration to .ts files

## Migration to TypeScript

To convert a JavaScript file to TypeScript:

1. Rename `.js` → `.ts`
2. Add explicit types instead of JSDoc
3. Fix any type errors
4. Update imports if needed

Example:
```typescript
// Before (JavaScript with JSDoc)
/**
 * @param {string} message
 * @returns {void}
 */
function logMessage(message) {
  console.log(message);
}

// After (TypeScript)
function logMessage(message: string): void {
  console.log(message);
}
```

## CI/CD Integration

Add type checking to your CI/CD pipeline:

```yaml
# .github/workflows/ci.yml
- name: Type Check
  run: npm run type-check
```

## Resources

- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [JSDoc Reference](https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html)
- [Vite + TypeScript](https://vitejs.dev/guide/features.html#typescript)
