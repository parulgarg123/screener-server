#!/usr/bin/env python3
from typing import Any, Dict, List
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from jugaad_data.nse import NSELive

# Initialize FastMCP server
mcp = FastMCP("screener")

# Constants
SCREENER_BASE_URL = "https://www.screener.in"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Set up output directory
OUTPUT_DIR = Path.home() / "Documents" / "StockData"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def make_screener_request(url: str, params: Dict = None, method: str = "GET", data: Dict = None, client: httpx.AsyncClient = None) -> Dict[str, Any]:
    """Make a request to screener.in with proper headers and error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/html",
        "X-Requested-With": "XMLHttpRequest",  # Required for AJAX requests
        "Referer": SCREENER_BASE_URL
    }

    if client is None:
        async with httpx.AsyncClient() as temp_client:
            return await make_request(temp_client, url, headers, params, method, data)
    else:
        return await make_request(client, url, headers, params, method, data)

async def make_request(client: httpx.AsyncClient, url: str, headers: Dict, params: Dict = None, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Helper function to make the actual request with session handling."""
    try:
        # First get the page to get CSRF token and cookies
        if method.upper() == "POST":
            page_response = await client.get(url.split('/api/')[0], headers=headers)
            page_response.raise_for_status()
            soup = BeautifulSoup(page_response.text, 'html.parser')
            csrf_token = soup.find('meta', {'name': 'csrf-token'})
            
            if csrf_token:
                headers['X-CSRFToken'] = csrf_token['content']
            
            response = await client.post(url, headers=headers, params=params, json=data, timeout=30.0)
        else:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            
        response.raise_for_status()
        content_type = response.headers.get('content-type', '')
        
        if content_type.startswith('application/json'):
            return response.json()
        return response.text
    except Exception as e:
        raise Exception(f"Error fetching data: {str(e)}")

def extract_initial_state(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract the initial Redux state from script tags."""
    try:
        for script in soup.find_all('script'):
            if script.string and ('window.__INITIAL_STATE__' in script.string or 'window.__PRELOADED_STATE__' in script.string):
                import re
                import json
                
                # Try to find the state object in the script
                state_match = re.search(r'window\.__(?:INITIAL|PRELOADED)_STATE__\s*=\s*({.*?});', script.string, re.DOTALL)
                if state_match:
                    try:
                        return json.loads(state_match.group(1))
                    except json.JSONDecodeError:
                        continue
                        
        return None
    except Exception as e:
        print(f"Error extracting initial state: {str(e)}")
        return None

async def fetch_expanded_section(url: str, section_id: str, company_id: str = None, initial_state: Dict = None) -> Dict[str, Any]:
    """Fetch expanded content for a collapsed section."""
    try:
        if 'cash' in section_id.lower() and company_id:
            # First try to get the data from initial state
            if initial_state and 'company' in initial_state:
                company_data = initial_state['company']
                if 'cashFlow' in company_data:
                    detailed_data = company_data['cashFlow'].get('detailed', {})
                    if detailed_data:
                        return detailed_data
            
            # If not in initial state, try with multiple session-aware requests
            async with httpx.AsyncClient() as client:
                # First establish a session with cookies
                homepage_resp = await client.get(SCREENER_BASE_URL)
                if homepage_resp.cookies:
                    client.cookies.update(homepage_resp.cookies)
                
                # Get the company page to get all required tokens
                company_url = f"{SCREENER_BASE_URL}/company/{company_id}/"
                headers = {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "User-Agent": USER_AGENT,
                    "Referer": SCREENER_BASE_URL
                }
                
                company_resp = await client.get(company_url, headers=headers)
                if company_resp.status_code == 200:
                    soup = BeautifulSoup(company_resp.text, 'html.parser')
                    csrf_token = soup.find('meta', {'name': 'csrf-token'})
                    
                    if csrf_token:
                        headers['X-CSRFToken'] = csrf_token['content']
                
                # Try different API endpoints with the established session
                for endpoint in [
                    f"/api/company/{company_id}/analysis/",
                    f"/api/company/{company_id}/financials/expanded/",
                    f"/api/company/{company_id}/cash-flow/"
                ]:
                    try:
                        expand_url = f"{SCREENER_BASE_URL}{endpoint}"
                        response = await client.post(
                            expand_url,
                            headers=headers,
                            json={
                                "type": "cash_flow",
                                "section": "expanded",
                                "consolidated": True,
                                "format": "detailed",
                                "with_sections": True
                            },
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data and isinstance(data, dict):
                                return data
                                
                    except Exception as e:
                        print(f"Failed for endpoint {endpoint}: {str(e)}")
                        continue
        # If not cash flow or previous attempts failed, try standard section expansion
        clean_id = section_id.lstrip('#').rstrip('/')
        expand_url = f"{url}section/{clean_id}/"
        
        try:
            return await make_screener_request(expand_url, method="GET")
        except Exception as e:
            print(f"Standard section expansion failed: {str(e)}")
            
        return None
    except Exception as e:
        print(f"Error in fetch_expanded_section: {str(e)}")
        return None

async def fetch_concall_transcript(url: str) -> str:
    """Fetch and extract the concall transcript content."""
    try:
        response = await make_screener_request(url)
        if isinstance(response, str):
            soup = BeautifulSoup(response, 'html.parser')
            
            # Try multiple possible selectors where transcript content might be
            transcript_selectors = [
                'div.content-text',  # Main content area
                'div[role="main"]',  # Main content wrapper
                'div.document-content',  # Document content area
                'div.white-space-pre-wrap'  # Pre-formatted text
            ]
            
            for selector in transcript_selectors:
                transcript_div = soup.select_one(selector)
                if transcript_div and transcript_div.text.strip():
                    # Clean up the text
                    text = transcript_div.get_text(separator='\n', strip=True)
                    # Remove multiple newlines
                    text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
                    return text
            
        return ""
    except Exception as e:
        print(f"Error fetching transcript: {str(e)}")
        return ""

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

async def parse_ratios(soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
    """Extract ratios from the page, including expanding collapsed sections."""
    ratios = {}
    
    # Process regular ratios
    for section in soup.select('.flex.flex-wrap, .company-ratios'):
        for ratio in section.select('li'):
            label = ratio.select_one('.name, div:first-child')
            value = ratio.select_one('.number, .font-bold')
            if label and value:
                label_text = label.text.strip()
                value_text = value.text.strip()
                if label_text and value_text and "View more" not in label_text:
                    ratios[label_text] = value_text
    
    # Handle expandable sections
    for expandable in soup.select('[data-reactid]'):  # Common attribute for expandable sections
        section_id = expandable.get('id') or expandable.get('data-section-id')
        if section_id and ('collapse' in section_id.lower() or 'expand' in section_id.lower()):
            expanded_data = await fetch_expanded_section(base_url, section_id)
            if expanded_data and isinstance(expanded_data, dict):
                for key, value in expanded_data.items():
                    if isinstance(value, (str, int, float)):
                        ratios[key] = str(value)
    
    return ratios

async def parse_tables(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    """Extract table data from the page, including expanding collapsed sections."""
    tables = []
    
    # Process regular tables
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

        # Handle table expansions
        # First check for expand button
        expand_button = table.find_next('button', string=lambda s: s and ('more' in s.lower() or 'expand' in s.lower()))
        section_id = None
        
        if expand_button:
            section_id = expand_button.get('data-section-id') or expand_button.parent.get('id')
            
        # If no explicit expand button, look for section IDs in the table or its container
        if not section_id:
            table_container = table.find_parent('div', class_='responsive-holder')
            if table_container:
                section_id = table_container.get('id') or table_container.get('data-section-id')
                
        # Enhanced handling for cash flows section
        if table_data["title"] == "Cash Flows":
            # Extract company ID - first try from canonical URL
            company_id = None
            company_link = soup.find('link', {'rel': 'canonical'})
            if company_link and 'href' in company_link.attrs:
                company_id = company_link['href'].rstrip('/').split('/')[-1]
            
            # If not found, try to get it from script tags
            if not company_id:
                for script in soup.find_all('script'):
                    script_text = script.string
                    if script_text and 'companyId' in script_text:
                        import re
                        match = re.search(r'companyId["\']?\s*:\s*["\']?(\d+)', script_text)
                        if match:
                            company_id = match.group(1)
                            break
            
            # Try multiple approaches to find the cash flow section
            cash_flow_selectors = [
                'section.cash-flow-section',
                'section.cash-flows',
                'div[data-section="cash-flow"]',
                'div.responsive-holder',
                'div[data-cash-flow]',
                'div[data-statement="cash-flow"]'
            ]
            
            # First try to find the section from the page structure
            for selector in cash_flow_selectors:
                cash_flow_container = table.find_parent(selector)
                if cash_flow_container:
                    # Try to find section ID from various attributes
                    for attr in cash_flow_container.attrs:
                        if any(term in attr.lower() for term in ['section', 'cash', 'flow', 'id', 'data']):
                            potential_id = cash_flow_container[attr]
                            if potential_id and isinstance(potential_id, str):
                                section_id = potential_id
                                break
                    
                    if section_id:
                        break
                        
            # If still no section ID, try alternative methods
            if not section_id and company_id:
                section_id = f"cash-flow-{company_id}"
                        
            # If we still don't have a section ID, try to find it from the URL
            if not section_id:
                # Look for any element that might contain the cash flow section URL
                cash_flow_link = soup.find('a', href=lambda h: h and 'cash-flow' in h.lower())
                if cash_flow_link:
                    # Extract section ID from the URL
                    section_id = cash_flow_link['href'].split('/')[-1]

            # Try to fetch expanded cash flow data
            if section_id and company_id:
                expanded_data = await fetch_expanded_section(base_url, section_id, company_id)
                if expanded_data and isinstance(expanded_data, dict):
                    # Process the expanded data based on its structure
                    if 'rows' in expanded_data:
                        # Direct rows data
                        for row in expanded_data['rows']:
                            if isinstance(row, list):
                                if row not in table_data["rows"]:
                                    table_data["rows"].append(row)
                            elif isinstance(row, dict):
                                row_data = [str(row.get(h, '')) for h in table_data["headers"]]
                                if row_data not in table_data["rows"]:
                                    table_data["rows"].append(row_data)
                    else:
                        # Try to extract detailed cash flow components
                        for category in ['operating', 'investing', 'financing']:
                            if category in expanded_data:
                                cat_data = expanded_data[category]
                                if isinstance(cat_data, dict):
                                    for key, values in cat_data.items():
                                        if isinstance(values, list):
                                            row_data = [f"{key}+"] + [str(v) for v in values]
                                            if row_data not in table_data["rows"]:
                                                table_data["rows"].append(row_data)
                        
                        # Process any other nested data
                        for key, values in expanded_data.items():
                            if key not in ['operating', 'investing', 'financing']:
                                if isinstance(values, list) and len(values) > 0:
                                    row_data = [key] + [str(v) for v in values]
                                    if row_data not in table_data["rows"]:
                                        table_data["rows"].append(row_data)
                                elif isinstance(values, dict):
                                    row_data = [key] + [str(values.get(h, '')) for h in table_data["headers"][1:]]
                                    if row_data not in table_data["rows"]:
                                        table_data["rows"].append(row_data)

        tables.append(table_data)
    
    return tables

async def parse_links(soup: BeautifulSoup, base_url: str) -> Dict[str, List]:
    """Extract related links and concall transcript URLs from the page."""
    company_links = []
    concall_links = []
    
    # Find the documents section
    documents_section = None
    for h2 in soup.find_all('h2'):
        if 'Documents' in h2.text:
            documents_section = h2.find_parent('div')
            break
    
    # First, collect concall links from documents section
    if documents_section:
        for link in documents_section.find_all('a'):
            href = link.get('href', '')
            text = link.text.strip()
            
            if href and text and ('concall' in href.lower() or 'transcript' in href.lower()):
                full_url = f"{base_url}{href}" if not href.startswith('http') else href
                transcript = await fetch_concall_transcript(full_url)
                concall_links.append({
                    "text": text,
                    "url": full_url,
                    "transcript": transcript
                })
    
    # Then collect company links from the whole page
    for link in soup.select('a'):
        href = link.get('href', '')
        text = link.text.strip()
        
        if href and text and '/company/' in href and '#' not in href:
            company_links.append({
                "text": text,
                "url": f"{base_url}{href}"
            })
    
    return {
        "company_links": company_links,
        "concall_links": concall_links
    }

def save_to_csv(data: Dict, filepath: Path, transcript_dir: Path = None) -> None:
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

    # Save company links
    if data["links"]["company_links"]:
        csv_content.append(['Related Company Links'])
        csv_content.append(['Link Text', 'URL'])
        for link in data["links"]["company_links"]:
            csv_content.append([link["text"], link["url"]])
            
    # Save concall links and transcripts
    if data["links"]["concall_links"]:
        csv_content.append([])
        csv_content.append(['Concall Links and Transcripts'])
        csv_content.append(['Date', 'URL', 'Transcript File', 'Transcript Content'])
        
        if transcript_dir:
            transcript_dir.mkdir(parents=True, exist_ok=True)
            
        for link in data["links"]["concall_links"]:
            file_path = ""
            if transcript_dir and link["transcript"]:
                # Create transcript filename from the link text (usually contains the date)
                transcript_file = transcript_dir / f"transcript_{link['text'].replace(' ', '_').replace('/', '_')}.txt"
                with open(transcript_file, 'w', encoding='utf-8') as f:
                    f.write(link["transcript"])
                file_path = str(transcript_file)
            
            csv_content.append([
                link["text"],
                link["url"],
                file_path or "No file saved",
                link["transcript"] or "No transcript available"
            ])

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
            "ratios": await parse_ratios(soup, f"{SCREENER_BASE_URL}{company_url}"),
            "tableData": await parse_tables(soup, f"{SCREENER_BASE_URL}{company_url}"),
            "links": {
                "companyUrl": f"{SCREENER_BASE_URL}{company_url}",
                "company_links": [],
                "concall_links": []
            }
        }
        
        # Extract links and concall transcripts
        links_data = await parse_links(soup, SCREENER_BASE_URL)
        data["links"].update(links_data)

        # Save to file
        timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
        filename = f"{data['marketData']['companyName'].replace(' ', '_')}_{timestamp}.csv"
        filepath = OUTPUT_DIR / filename
        
        # Create transcript directory
        transcript_dir = filepath.parent / f"{data['marketData']['companyName'].replace(' ', '_')}_transcripts"
        
        # Save data with transcripts
        save_to_csv(data, filepath, transcript_dir)
        
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
        db_path = "/Users/parulgarg/Documents/GitHub/masterBroker/PythonAPI/broker_data.db"
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
            
            

@mcp.tool()
async def fetch_live_price(ticker: str) -> str:
    """Fetch the live closing price for a stock from screener.in.

    Args:
        ticker (str): The NSE stock ticker symbol to fetch price data for (e.g. "RELIANCE", "TCS", "HDFC").
            Must be a valid NSE symbol in uppercase, without any spaces or special characters.

    Returns:
        str: The closing price of the stock

    Raises:
        ValueError: If the ticker symbol is invalid or not found
    """
    import re
    
    # Validate ticker format
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
        
    # Check ticker format (uppercase letters and numbers only)
    if not re.match("^[A-Z0-9]+$", ticker):
        raise ValueError("Ticker must contain only uppercase letters and numbers")
    
    try:
        print(f"Fetching price data for {ticker} from screener.in...")
        
        # First search for the company
        search_data = await make_screener_request(
            f"{SCREENER_BASE_URL}/api/company/search/",
            params={"q": ticker}
        )
        
        if not search_data:
            raise ValueError(f"No results found for ticker {ticker}")
            
        print("Search response:", search_data)
        
        # Get company details page
        if not search_data or not isinstance(search_data, list) or len(search_data) == 0:
            raise ValueError(f"No matching company found for ticker {ticker}")
            
        company_url = search_data[0]["url"]
        print(f"Found company URL: {company_url}")
        
        company_response = await make_screener_request(f"{SCREENER_BASE_URL}{company_url}")
        
        if not isinstance(company_response, str):
            raise ValueError(f"Invalid response type from screener.in: {type(company_response)}")
            
        print(f"Response length: {len(company_response)}")
            
        # Parse the response with BeautifulSoup
        soup = BeautifulSoup(company_response, 'html.parser')
        
        # Find the current price
        for item in soup.select('.company-ratios li'):
            label = item.select_one('.name')
            value = item.select_one('.number')
            if label and value and "Current Price" in label.text:
                price = value.text.strip().replace(',', '')
                price = price.replace('₹', '').strip()  # Remove rupee symbol if present
                try:
                    float_price = float(price)
                    print(f"Found price: {float_price}")
                    return str(float_price)
                except ValueError:
                    print(f"Could not convert price '{price}' to float")
                    continue
                
        raise ValueError("Could not find price in the response")
            
    except Exception as e:
        print(f"Error fetching price: {str(e)}")
        raise ValueError(f"Failed to fetch price for {ticker}: {str(e)}")

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
