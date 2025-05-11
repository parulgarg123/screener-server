# Screener.in Stock Data Extractor

A command-line tool to extract stock data from screener.in and save it as CSV.

## Features

- Extracts comprehensive stock data including:
  - Company Information (name, market cap, current price)
  - All Financial Ratios
  - Table Data (quarterly results, profit & loss, balance sheet, etc.)
  - Related Links
- Saves data in a well-formatted CSV file
- Organizes files by date and company name
- Automatically expands and captures all available data

## Installation

1. Make sure you have Node.js installed
2. Clone or download this repository
3. Navigate to the project directory
4. Run `npm install` to install dependencies
5. Run `npm run build` to compile the TypeScript code

## Usage

### Using the Shell Script

```bash
./extract-stock.sh "STOCK_NAME"
```

Example:
```bash
./extract-stock.sh "TCS"
./extract-stock.sh "Infosys"
```

### Manual Usage

```bash
node build/index.js "STOCK_NAME"
```

## Output

The extracted data will be saved in CSV format at:
`~/Documents/StockData/COMPANY_NAME_TIMESTAMP.csv`

The CSV file includes:
- Company Information Section
  - Company Name
  - Company URL
  - Market Cap
  - Current Price
  - 52 Week High/Low
- Key Ratios Section
  - All available financial ratios
- Table Data Sections
  - Each table with headers and data
- Related Links Section
  - Text and URLs of related companies

## Error Handling

- Displays clear error messages if:
  - Stock name is not provided
  - Stock is not found
  - Network errors occur
  - Any data extraction fails

## Note

Please ensure you comply with screener.in's terms of service and usage policies when using this tool.
