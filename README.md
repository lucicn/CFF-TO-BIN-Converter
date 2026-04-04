# CFF TO BIN Converter

Simple GUI tool to convert Mercedes-Benz CFF (Caesar Flash File) containers to binary files.

## Features

- Load and parse CFF flash container files
- Display flash metadata (name, author, checksum, segments)
- CRC32 checksum verification
- Export all flash segments as a single combined `.bin` file
- Clean dark-themed Tkinter GUI

## Screenshot

![CFF TO BIN Converter](screenshot.png)

## Requirements

- Python 3.8+
- No external dependencies (uses only standard library: `tkinter`, `struct`, `threading`)

## Usage

```bash
python cff_to_bin.py
```

1. Click **Load CFF File** to select a `.cff` file
2. Review the file info (flash name, author, checksum, segment count)
3. Click **Convert to BIN** to save the extracted binary data

## How It Works

The parser implements the CFF binary format parsing algorithm:

1. **Stub Header** (0x410 bytes) - identifies file type (CBF/CFF)
2. **Bitflag-driven field parsing** - a bitflag word controls which fields are present in each record
3. **Flash Header** - metadata, table references, version info
4. **Data Blocks** - groups of flash segments with qualifier info
5. **Flash Segments** - individual firmware binary chunks with address/length metadata
6. **CRC32 Checksum** - file integrity verification using a custom lookup table

Parsing logic ported from [CFFFlashFileTools](https://github.com/Xplatforms/CFFFlashFileTools) (C++/Qt).

## License

GPL-3.0