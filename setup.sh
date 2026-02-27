#!/bin/bash
# Brooke Quick Start Script

echo "=========================================="
echo "BROOKE - FastMoss Video Scraping Pipeline"
echo "=========================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check for .env
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your AWS credentials"
fi

echo ""
echo "Setup complete! Next steps:"
echo ""
echo "1. Edit .env with your credentials:"
echo "   nano .env"
echo ""
echo "2. Initialize DynamoDB:"
echo "   python brooke_main.py --init-db"
echo ""
echo "3. Run test scrape:"
echo "   python brooke_main.py -p 'wireless earbuds' --test"
echo ""
echo "4. Start API server:"
echo "   python api_server.py"
echo ""
