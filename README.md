# MKV to MP4 UI

A modern, user-friendly PyQt6 GUI application for batch converting MKV video files to MP4 format using FFmpeg. Perfect for converting movie collections ripped with MakeMKV or HandBrake into a more universally compatible format.

![MKV to MP4 Converter Screenshot](https://raw.githubusercontent.com/scottpeterman/mkvtomp4ui/refs/heads/main/screenshots/app_screenshot.png)

## Features

🎬 **Batch Conversion** - Select and convert multiple MKV files at once  
⚡ **Real-time Progress** - Live FFmpeg output with encoding speed and ETA  
🔧 **Configurable Settings** - Choose video/audio codecs, quality, and presets  
📁 **Flexible Output** - Convert to source folder or choose custom output directory  
🖥️ **Cross-platform** - Works on Windows, macOS, and Linux  
📦 **Self-contained** - Automatic FFmpeg download and installation  
🎯 **User-friendly** - Modern GUI with progress tracking and detailed logs  

## Installation

### From PyPI (Recommended)

```bash
pip install mkv2mp4ui
```

### From Source

```bash
git clone https://github.com/scottpeterman/mkvtomp4ui.git
cd mkvtomp4ui
pip install -r requirements.txt
python -m mkv2mp4ui.main
```

## Usage

### Launch the Application

After installation, you can start the application in several ways:

```bash
# Command line
mkv2mp4ui

# Or as a GUI application
mkv2mp4ui-gui

# Or from Python
python -m mkv2mp4ui.main
```

### Using the GUI

#### 1. **Select Source Folder**
- Click "Select Folder with MKV Files" 
- Browse to the directory containing your MKV files
- The application will automatically scan for all `.mkv` files in the folder and subfolders

#### 2. **Choose Output Location** (Optional)
- By default, MP4 files are saved in the same location as the source MKV files
- Click "Select Output Folder" to choose a different destination
- Useful for organizing converted files separately

#### 3. **Configure Conversion Settings**

**Video Codec:**
- `libx264` - Widely compatible H.264 encoding (recommended)
- `libx265` - More efficient H.265/HEVC encoding (smaller files)
- `copy` - Copy video stream without re-encoding (fastest, preserves quality)

**Audio Codec:**
- `aac` - Standard AAC audio (recommended for compatibility)
- `mp3` - MP3 audio encoding
- `copy` - Copy audio stream without re-encoding

**Quality (CRF):**
- Range: 0-51 (lower = better quality, larger files)
- Recommended: 18-28
- Default: 23 (good balance of quality and file size)

**Preset:**
- `veryfast` to `veryslow` - Controls encoding speed vs compression efficiency
- `medium` is the default and recommended for most users

#### 4. **Select Files for Conversion**
- All discovered MKV files are listed with checkboxes
- Use "Select All" to quickly select/deselect all files
- Manually check/uncheck individual files as needed
- The status shows "X/Y files selected"

#### 5. **Start Conversion**
- Click "Start Conversion" to begin the batch process
- Monitor real-time progress with:
  - **Progress bar** showing overall completion
  - **Status display** with current file, progress percentage, encoding speed, and ETA
  - **Detailed log** showing live FFmpeg output with color-coded messages
- Use "Stop Conversion" to cancel the process if needed

#### 6. **Monitor Progress**
The application provides comprehensive feedback:

- **Blue text**: FFmpeg progress information (frame rate, speed, bitrate)
- **Orange text**: Warnings or non-critical issues
- **Red text**: Errors or failures
- **Progress percentage**: How much of the current file has been processed
- **Encoding speed**: How fast the conversion is running (e.g., "13.5x" = 13.5 times real-time)
- **ETA**: Estimated time of completion

#### 7. **Completion**
- A dialog will notify you when all conversions are complete
- Check the log for any errors or warnings
- Converted MP4 files will be in your specified output location

## FFmpeg Installation

The application includes an automatic FFmpeg downloader:

- **First run**: If FFmpeg is not found, a dialog will offer to download it automatically
- **Manual installation**: You can also download FFmpeg manually and place it in the application directory
- **System installation**: The app will use FFmpeg if it's already installed in your system PATH

## Common Use Cases

### Converting Movie Collections
Perfect for converting movies ripped with MakeMKV or HandBrake:
```
Source: /Movies/Lord_of_the_Rings/
├── Fellowship.mkv
├── Two_Towers.mkv
└── Return_of_the_King.mkv

Output: /Movies/Lord_of_the_Rings/
├── Fellowship.mp4
├── Two_Towers.mp4
└── Return_of_the_King.mp4
```

### Quality vs Speed Settings

**Fast conversion (copy streams):**
- Video Codec: `copy`
- Audio Codec: `copy`
- Use when: MKV container is the only issue, codecs are already compatible

**High quality re-encoding:**
- Video Codec: `libx264` or `libx265`
- Audio Codec: `aac`
- Quality (CRF): `18-20`
- Preset: `slow` or `slower`

**Balanced conversion:**
- Video Codec: `libx264`
- Audio Codec: `aac`
- Quality (CRF): `23`
- Preset: `medium`

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 4GB RAM recommended for HD video conversion
- **Storage**: Ensure adequate free space (MP4 files may be larger or smaller than MKV depending on settings)

## Troubleshooting

### FFmpeg Not Found
- Use the automatic download feature in the application
- Or manually download from [FFmpeg.org](https://ffmpeg.org/download.html)
- Ensure `ffmpeg.exe` is in your PATH or application directory

### Conversion Failures
- Check the conversion log for detailed error messages
- Verify source files are not corrupted
- Ensure sufficient disk space for output files
- Try different codec settings if specific files fail

### Performance Issues
- Use "copy" codecs when possible for fastest conversion
- Choose faster presets (`fast`, `veryfast`) for quicker processing
- Close other applications to free up system resources
- Consider converting files individually if batch processing is too slow

## Contributing

Contributions are welcome! Please feel free to submit pull requests, bug reports, or feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI
- Uses [FFmpeg](https://ffmpeg.org/) for video conversion
- Inspired by the need for a simple, user-friendly MKV to MP4 converter

---

**Note**: This application is designed for personal use with your own video files. Ensure you have the right to convert any video files you process.