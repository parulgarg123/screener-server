#!/usr/bin/env python3
from typing import Any, Dict, List
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("screener")

# Constants
SCREENER_BASE_URL = "https://www.screener.in"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Set up output directory
OUTPUT_DIR = Path.home() / "Documents" / "StockData"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def make_screener_request(url: str, params: Dict = None) -> Dict[str, Any]:
    """Make a request to screener.in with proper headers and error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/html"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        except Exception as e:
            raise Exception(f"Error fetching data: {str(e)}")

def parse_market_data(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract market data from the page."""
    data = {
        "companyName": "",
        "marketCap": "",
        "currentPrice": "",
        "highLow": ""
    }
    
    data["companyName"] = soup.find('h1').text.strip()
    
    for item in soup.select('.company-ratios li'):
        label = item.select_one('.name').text.strip()
        value = item.select_one('.number').text.strip()
        
        if "Market Cap" in label:
            data["marketCap"] = value
        elif "Current Price" in label:
            data["currentPrice"] = value
        elif "52 Week High / Low" in label:
            data["highLow"] = value
            
    return data

def parse_ratios(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract ratios from the page."""
    ratios = {}
    for section in soup.select('.flex.flex-wrap, .company-ratios'):
        for ratio in section.select('li'):
            label = ratio.select_one('.name, div:first-child')
            value = ratio.select_one('.number, .font-bold')
            if label and value:
                label_text = label.text.strip()
                value_text = value.text.strip()
                if label_text and value_text and "View more" not in label_text:
                    ratios[label_text] = value_text
    return ratios

def parse_tables(soup: BeautifulSoup) -> List[Dict]:
    """Extract table data from the page."""
    tables = []
    for table in soup.select('table.data-table'):
        table_data = {
            "title": "",
            "headers": [],
            "rows": []
        }

        title_elem = table.find_previous('h2')
        if title_elem:
            table_data["title"] = title_elem.text.strip()

        table_data["headers"] = [th.text.strip() for th in table.select('thead th')]
        
        for row in table.select('tbody tr'):
            row_data = [cell.text.strip() for cell in row.select('td')]
            table_data["rows"].append(row_data)

        tables.append(table_data)
    return tables

def parse_links(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    """Extract related links from the page."""
    links = []
    for link in soup.select('a'):
        href = link.get('href', '')
        text = link.text.strip()
        if href and '/company/' in href and '#' not in href and text:
            links.append({
                "text": text,
                "url": f"{base_url}{href}"
            })
    return links

def save_to_csv(data: Dict, filepath: Path) -> None:
    """Save the extracted data to a CSV file."""
    csv_content = []
    csv_content.append(['Company Information'])
    csv_content.append(['Company Name', data["marketData"]["companyName"]])
    csv_content.append(['Company URL', data["links"]["companyUrl"]])
    csv_content.append(['Market Cap', data["marketData"]["marketCap"]])
    csv_content.append(['Current Price', data["marketData"]["currentPrice"]])
    csv_content.append(['52 Week High/Low', data["marketData"]["highLow"]])
    csv_content.append([])

    csv_content.append(['Key Ratios'])
    for key, value in data["ratios"].items():
        csv_content.append([key, value])
    csv_content.append([])

    for table in data["tableData"]:
        csv_content.append([table["title"]])
        csv_content.append(table["headers"])
        csv_content.extend(table["rows"])
        csv_content.append([])

    if data["links"]["relatedLinks"]:
        csv_content.append(['Related Links'])
        csv_content.append(['Link Text', 'URL'])
        for link in data["links"]["relatedLinks"]:
            csv_content.append([link["text"], link["url"]])

    with open(filepath, 'w', encoding='utf-8') as f:
        for row in csv_content:
            f.write(','.join(f'"{str(cell)}"' for cell in row) + '\n')

@mcp.tool()
async def get_stock_data(stock_name: str) -> Dict:
    """Get detailed stock data from screener.in.
    
    Args:
        stock_name: Name of the stock to search for
    """
    try:
        # Search for the stock
        search_data = await make_screener_request(
            f"{SCREENER_BASE_URL}/api/company/search/",
            params={"q": stock_name}
        )

        if not search_data:
            return {"error": "No results found for the given stock name."}

        # Get company details
        company_url = search_data[0]["url"]
        company_response = await make_screener_request(f"{SCREENER_BASE_URL}{company_url}")
        
        soup = BeautifulSoup(company_response, 'html.parser')
        
        # Extract all data
        data = {
            "marketData": parse_market_data(soup),
            "ratios": parse_ratios(soup),
            "tableData": parse_tables(soup),
            "links": {
                "companyUrl": f"{SCREENER_BASE_URL}{company_url}",
                "relatedLinks": parse_links(soup, SCREENER_BASE_URL)
            }
        }

        # Save to file
        timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
        filename = f"{data['marketData']['companyName'].replace(' ', '_')}_{timestamp}.csv"
        filepath = OUTPUT_DIR / filename
        
        save_to_csv(data, filepath)
        
        # Return the data along with the file path
        return {
            "message": "Data fetched and saved successfully.",
            "filePath": str(filepath),
            "data": data
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_broker_data(broker_name: str = None, fetch_only_latest: bool = True) -> List[Dict[str, Any]]:
    """Fetch broker data based on the provided parameters.

    Args:
        broker_name: Optional; Name of the broker to fetch data for. If not provided, fetches data for all brokers.
        fetch_only_latest: Boolean; If True, fetches only the latest data for each broker. Defaults to True.

    Returns:
        A list of dictionaries containing broker data with keys: BrokerName, holdings, and dateTime.
    """
    import sqlite3
    import requests
    from datetime import datetime

    api_url = "http://127.0.0.1:5000/printEverything/"
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        api_data = response.json()

        result = []
        for broker, holdings in api_data.items():
            if broker_name and broker != broker_name:
                continue
            result.append({
                "BrokerName": broker,
                "holdings": holdings,
                "dateTime": datetime.now().isoformat()
            })
        return {
            "source": "API",
            "data": result if fetch_only_latest else result
        }

    except requests.RequestException:
        db_path = "/Users/parulgarg/Documents/GitHub/masterBroker/broker_data.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = "SELECT BrokerName, holdings, dateTime FROM broker_data"
        if broker_name:
            query += " WHERE BrokerName = ?"
            cursor.execute(query, (broker_name,))
        else:
            cursor.execute(query)

        rows = cursor.fetchall()
        conn.close()

        if fetch_only_latest:
            latest_data = {}
            for broker, holdings, date_time in rows:
                if broker not in latest_data or latest_data[broker]["dateTime"] < date_time:
                    latest_data[broker] = {"holdings": holdings, "dateTime": date_time}
            return {
                "source": "DB",
                "data": [{"BrokerName": broker, **data} for broker, data in latest_data.items()]
            }
        else:
            return {
                "source": "DB",
                "data": [{"BrokerName": broker, "holdings": holdings, "dateTime": date_time} for broker, holdings, date_time in rows]
            }

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
