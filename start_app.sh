#!/bin/bash

# TCG Deck Analyzer - Start Script
# Simple script to activate the virtual environment and run the Streamlit app

echo "🚀 Starting TCG Deck Analyzer..."
echo ""

# Activate virtual environment
source .venv/bin/activate

# Run the Streamlit app
echo "✅ App running at: http://localhost:8501"
echo ""
echo "📍 In Codespaces: Click 'Ports' tab and open the forwarded URL"
echo "📍 SSH tunnel: Use port forwarding to access from your machine"
echo ""
streamlit run app.py
