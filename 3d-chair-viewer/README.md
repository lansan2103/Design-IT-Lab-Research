# 3D Chair Viewer

A modern, interactive 3D chair viewer built with Three.js and featuring an Apple-inspired design.

## Features

- **Interactive 3D Model**: A white chair with backrest (no armrests) rendered in 3D
- **Mouse Controls**: 
  - Scroll wheel to zoom in and out
  - Click and drag to rotate the view around the chair
- **Modern Design**: Clean, Apple-inspired interface with gradient backgrounds and glass-morphism effects
- **Responsive**: Works on both desktop and mobile devices
- **Real-time Rendering**: Smooth 60fps rendering with shadows and lighting

## How to Use

1. **Open the file**: Simply open `index.html` in any modern web browser
2. **Zoom**: Use your mouse wheel to zoom in and out of the chair
3. **Rotate**: Click and drag on the viewer to rotate the camera around the chair
4. **Explore**: The chair will rotate smoothly as you drag, allowing you to view it from any angle

## Technical Details

- **Framework**: Three.js for 3D rendering
- **Styling**: Pure CSS with modern design principles
- **Browser Support**: Works in all modern browsers with WebGL support
- **Performance**: Optimized for smooth 60fps rendering

## File Structure

```
3d-chair-viewer/
├── index.html          # Main HTML file with embedded CSS and JavaScript
└── README.md          # This file
```

## Browser Compatibility

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Development

The viewer is built as a single HTML file for simplicity and easy deployment. All styles and JavaScript are embedded within the HTML file, making it completely self-contained.

To modify the chair:
- Edit the `createChair()` function in the JavaScript section
- Adjust colors, dimensions, or add new geometric shapes
- The chair is built using basic Three.js geometries (BoxGeometry) for simplicity

## License

This project is open source and available under the MIT License. 