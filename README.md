# Drive Comparison Tool

A modern and efficient file comparison and synchronization tool that helps you keep your drives in sync.

## Features

- **File Comparison**: Compare files between two drives based on file name, size, and modification time
- **Deep Scanning**: Detect identical files in different locations to prevent duplication
- **Performance-Focused**: Efficiently processes large file sets with minimal memory usage
- **Modern UI**: Clean, modern interface with custom styling
- **Two-Phase Operation**: First scan to identify differences, then update to synchronize files
- **Detailed Reports**: View comprehensive reports of new, modified, missing, and duplicate files

## Installation

1. Ensure you have Python 3.7+ installed on your system
2. Clone this repository:
   ```
   git clone https://github.com/yourusername/compare-drives.git
   cd compare-drives
   ```
3. Install the required dependencies:
   ```
   pip install customtkinter pillow
   ```

## Usage

1. Run the application:
   ```
   python main.py
   ```

2. **Scan Phase**:
   - Select your destination drive (the one you want to update)
   - Select the source drive (the one with newer files)
   - Choose an output folder to store logs and results
   - Configure scan options (e.g., deep scan to find files in different locations)
   - Click "Start Scan" to begin the comparison

3. **Update Phase**:
   - After the scan completes, review the differences
   - Choose how to handle duplicate files (copy to new location, skip, or ask each time)
   - Click "Update Destination" to copy newer files to the destination

## How It Works

The tool works in two distinct phases:

1. **Scan Phase**: 
   - Indexes all files in both directories
   - Compares files by name, size, and modification time
   - If deep scan is enabled, identifies files that exist in different locations
   - Identifies new, modified, and missing files
   - Saves results for later use

2. **Update Phase**:
   - Uses the saved scan results
   - Copies new and modified files from source to destination
   - Optionally handles duplicate files based on user preference
   - Generates a detailed log of all actions

## Performance Considerations

- Uses efficient indexing for O(1) lookups
- Compares metadata only (not content) for initial scan
- Two-phase scanning: quick relative path comparison followed by optional deep scan
- Uses memory-efficient data structures

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
