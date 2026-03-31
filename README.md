# R15 Template Designer
Also known as "Conundrum by Este" - A robust, full-featured Roblox R15 Shirt visual editor and template generator.

## Features
- Full desktop capability powered by **Electron**
- Intuitive drag-and-drop layer management 
- Multi-component layout with presets for fullbleed, meme tees, mirrors, and more
- Powerful freeform drawing tools and word art integrated workflows

## Installation and Usage

### Prerequisites
- Node.js installed

### Setup App
To use this as a standalone desktop application:
1. Clone the repository and enter the directory:
   ```bash
   git clone https://github.com/estevanhernandez-stack-ed/r15Template-Designer.git
   cd r15Template-Designer
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Launch the application:
   ```bash
   npm start
   ```

### Python Helper Scripts
If you want to use the underlying python compositing engine without the UI (`roblox_shirt_maker.py`), you need:
- Python 3.x
- `Pillow` library installed (`pip install Pillow`)

```bash
# Example: create a single shirt with automatically-determined base color
python roblox_shirt_maker.py art.png
```

## Authors
- 626Labs
- Conundrum by Este
