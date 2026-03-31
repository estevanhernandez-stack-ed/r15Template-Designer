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

### Quick Install (Windows)
If you want to install this on another Windows PC:
1. Install [Node.js](https://nodejs.org/).
2. Open a terminal and clone the repository:
   ```bash
   git clone https://github.com/estevanhernandez-stack-ed/r15Template-Designer.git
   cd r15Template-Designer
   ```
3. Install dependencies and build the Windows installer:
   ```bash
   npm install
   npm run build
   ```
4. Navigate to the `dist/` folder and double click `R15 Template Designer Setup 1.0.0.exe` to install the app.
**(Alternatively, you can just take the `dist/R15 Template Designer Setup 1.0.0.exe` file and copy it to a USB drive to install directly on another computer without needing to compile it!)**

### Development Mode
To just run it without installing:
   ```bash
   npm install
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
