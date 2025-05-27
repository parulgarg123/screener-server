# Screener MCP Server

A Model Context Protocol (MCP) server that provides tools for fetching and analyzing stock data from screener.in. This server integrates with Claude to enable stock data analysis capabilities.

## Available Tools

1. `get_stock_data`
   - Purpose: Fetch detailed stock information
   - Input: Stock name
   - Output: Comprehensive stock data including company info, financials, ratios, and analysis
   - Example Output Location: `~/Documents/StockData/COMPANY_NAME_TIMESTAMP.csv`

2. `fetch_live_price`
   - Purpose: Get real-time stock price
   - Input: Stock ticker symbol (NSE symbol in uppercase)
   - Output: Current stock price
   - Example: "1234.56" (as string)

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Dependencies
- httpx: HTTP client library
- bs4: BeautifulSoup4 for HTML parsing
- mcp: Model Context Protocol library
- pathlib: Object-oriented filesystem paths

### Mac Installation
```bash
# Clone the repository
git clone <repository-url>
cd screener-mcp

# Run the server (automatically sets up virtual environment and installs dependencies)
./run-server.sh
```

### Windows Installation
```batch
# Clone the repository
git clone <repository-url>
cd screener-mcp

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

## Usage with Claude

### MCP Configuration

#### Mac Configuration
Add the following to your MCP configuration:
```json
{
  "screener": {
    "command": "/path/to/your/venv/bin/python3",
    "args": ["/path/to/your/screener-server/server.py"]
  }
}
```
Example:
```json
{
  "screener": {
    "command": "/Users/username/Documents/screener-mcp/venv/bin/python3",
    "args": ["/Users/username/Documents/screener-mcp/server.py"]
  }
}
```

#### Windows Configuration
Add the following to your MCP configuration:
```json
{
  "screener": {
    "command": "C:\\Path\\To\\Your\\venv\\Scripts\\python.exe",
    "args": ["C:\\Path\\To\\Your\\screener-mcp\\server.py"]
  }
}
```
Example:
```json
{
  "screener": {
    "command": "C:\\Users\\username\\Documents\\screener-mcp\\venv\\Scripts\\python.exe",
    "args": ["C:\\Users\\username\\Documents\\screener-mcp\\server.py"]
  }
}
```

### Using the Tools

1. First ensure the virtual environment is set up and dependencies are installed using the provided scripts (run-server.sh or run-server.bat)
2. Configure the MCP server as shown above with your actual paths
3. The server will be available for Claude to connect to
4. Use the following MCP tools in your Claude conversations:

### Example: Getting Detailed Stock Data

```python
<use_mcp_tool>
<server_name>screener</server_name>
<tool_name>get_stock_data</tool_name>
<arguments>
{
    "stock_name": "TCS"
}
</arguments>
</use_mcp_tool>
```

The tool will return:
- Company Information (name, market cap, current price)
- Key Financial Ratios
- Quarterly Results
- Profit & Loss Statements
- Balance Sheet Data
- Cash Flow Statements
- Related Company Links
- Concall Transcripts (if available)

### Example: Getting Live Stock Price

```python
<use_mcp_tool>
<server_name>screener</server_name>
<tool_name>fetch_live_price</tool_name>
<arguments>
{
    "ticker": "TCS"
}
</arguments>
</use_mcp_tool>
```

## Error Handling

The server provides detailed error messages for common scenarios:

1. Invalid Stock Name/Ticker:
   - "No results found for the given stock name."
   - "Ticker must contain only uppercase letters and numbers"

2. Network Issues:
   - "Error fetching data: Connection error"
   - "Failed to fetch price: Network timeout"

3. Rate Limiting:
   - Error messages from screener.in's rate limiting system

4. Data Parsing:
   - "Could not find price in the response"
   - "Error extracting initial state"

## Data Storage

1. Stock Data CSV:
   - Location: `~/Documents/StockData/COMPANY_NAME_TIMESTAMP.csv`
   - Format: Organized sections for different types of data
   - Automatic creation of directories if they don't exist

2. Concall Transcripts:
   - Location: `~/Documents/StockData/COMPANY_NAME_transcripts/`
   - Format: Individual text files for each transcript
   - Named with date and company information

## Development

### Project Structure
```
screener-mcp/
├── server.py        # Main MCP server implementation
├── requirements.txt # Python dependencies
├── run-server.sh   # Mac/Linux startup script
├── run-server.bat  # Windows startup script
└── README.md       # Documentation
```

### Adding New Features
1. Extend the server.py file with new MCP tools
2. Follow the existing pattern of using @mcp.tool() decorator
3. Implement proper error handling and validation
4. Update documentation with new tools

### Contributing
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear documentation
4. Ensure code follows existing patterns and includes error handling

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Notes

- Please ensure you comply with screener.in's terms of service and usage policies.
- The server implements rate limiting and respectful crawling practices.
- Data accuracy depends on screener.in's data availability and accuracy.
- Some features may require screener.in premium membership.
