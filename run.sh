#!/bin/bash

# Check if the virtual environment already exists
if [ ! -d "venv" ]; then
    echo "Creating a virtual environment..."
    python3 -m venv venv

    # Activate the virtual environment
    source venv/bin/activate

    echo "Installing the required packages..."
    pip install discord aiohttp beautifulsoup4 selenium
else
    # Activate the virtual environment
    source venv/bin/activate
fi

# Grant execute permissions to chromedriver
chmod +x chromedriver

# Run the bot
python onionsearch.py
