# Glazed Client Installer

![Python](https://img.shields.io/badge/python-3.9+-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-required-orange)
![License](https://img.shields.io/badge/License-GPLv3-green.svg)

A modern PyQt5-based installer for the [Glazed Client](https://github.com/realnnpg/Glazed) (Meteor Client add-on).  
It provides a sleek UI with animated backgrounds, custom dialogs, and an easy way to install the client for supported Minecraft versions.

## Features
- Modern, frameless PyQt5 UI  
- Animated starfield and constellation background  
- Version selector for Glazed Client  
- Auto-update check from remote server  
- Smooth button and card hover animations  
- Simple one-click installation

## Requirements
- Python 3.9+  
- Dependencies listed in `requirements.txt`

## Installation
1. Clone or download this repository.  
2. Install the dependencies:  
```bash
pip install -r requirements.txt
```

## Usage
Run the installer with:  
```bash
python main.py
```

## Supported Minecraft Versions
- 1.21.4  
- 1.21.5  

The installer will automatically download the correct `.jar` file for the chosen version.

## Download
[![Download Latest Release](https://img.shields.io/badge/%20Download%20Latest%20Release-blue?style=for-the-badge&logo=github)](https://github.com/szpuszi/glazed-client-installer/releases/latest)


## Notes
- Make sure Minecraft is closed during installation.  
- The installer will save version information in your home directory as `.glazed_version.txt`.

## Contributing
Contributions, issues and feature requests are welcome!  
Feel free to open an [issue](../../issues/) or submit a pull request.


## License
This project is licensed under the [GNU General Public License v3.0](LICENSE).  
You are free to use, modify, and distribute it under the terms of the GPL-3.0.
