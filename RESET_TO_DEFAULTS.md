# Reset Configuration to Defaults

## Problem
The optimized configuration preset has very strict blank page detection parameters that may classify all pages as blank:
- Variance Threshold: 238.83 (vs default 100)
- Edge Threshold: 12386 (vs default 50)
- White Pixel Ratio: 0.9929 (vs default 0.95)

## Solution

### Option 1: Manual Reset (Quick Fix)
1. Open the web UI in your browser
2. Press Ctrl+F5 to hard refresh (clear cache)
3. Click "Show Options" to expand configuration
4. Manually change values back to defaults:
   - Variance Threshold: **100**
   - Edge Threshold: **50**
   - White Pixel Ratio: **0.95**
   - Use Edge Detection: **checked**
5. Process your PDF again

### Option 2: Reset via Browser Console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Paste and run:
```javascript
document.getElementById('varianceThreshold').value = 100;
document.getElementById('edgeThreshold').value = 50;
document.getElementById('whitePixelRatio').value = 0.95;
document.getElementById('useEdgeDetection').checked = true;
console.log('Reset to defaults!');
```

### Option 3: Don't Use Optimized Preset
Simply don't click "Load Selected Preset" for the Optimized option. The default "Current" preset will work fine.

## Verification
After resetting, when you click "Process PDF", open the browser console (F12) and you should see:
```
Starting processing with config: {
  variance_threshold: 100,
  edge_threshold: 50,
  white_pixel_ratio: 0.95,
  ...
}
```

If you see values like 238.83, 12386, 0.9929 - those are the optimized (too strict) values.
