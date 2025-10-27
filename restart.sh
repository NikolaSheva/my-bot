#!/bin/bash
echo "Stopping bot..."
pkill -f "python src/main.py"
sleep 3
echo "Starting bot..."
python src/main.py
