from typing import Any, Dict, Optional
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("crypto-tracker")

# Constants
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
USER_AGENT = "crypto-tracker/1.0"

async def make_coingecko_request(url: str) -> Optional[Dict[str, Any]]:
    """Make a request to the CoinGecko API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API request failed: {e}")
            return None

def format_price(price_data: Dict[str, Any]) -> str:
    """Format price data into a readable string."""
    name = price_data.get('name', 'Unknown')
    symbol = price_data.get('symbol', '').upper()
    current_price = price_data.get('current_price', 0)
    market_cap = price_data.get('market_cap', 0)
    volume_24h = price_data.get('total_volume', 0)
    price_change_24h = price_data.get('price_change_percentage_24h', 0)
    
    # Format large numbers
    def format_number(num):
        if num >= 1e12:
            return f"${num/1e12:.2f}T"
        elif num >= 1e9:
            return f"${num/1e9:.2f}B"
        elif num >= 1e6:
            return f"${num/1e6:.2f}M"
        elif num >= 1e3:
            return f"${num/1e3:.2f}K"
        else:
            return f"${num:.2f}"
    
    result = f"""
{name} ({symbol})
Price: ${current_price:,.2f}
24h Change: {price_change_24h:+.2f}%
Market Cap: {format_number(market_cap)}
24h Volume: {format_number(volume_24h)}
    """.strip()
    
    return result

@mcp.tool()
async def get_crypto_price(symbol: str) -> str:
    """Get current price information for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'bitcoin', 'ethereum', 'dogecoin')
    """
    # Convert symbol to lowercase for API
    symbol = symbol.lower()
    
    url = f"{COINGECKO_API_BASE}/simple/price?ids={symbol}&vs_currencies=usd&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true"
    
    data = await make_coingecko_request(url)
    
    if not data:
        return f"Failed to fetch price data for {symbol}. Please check the symbol and try again."
    
    if symbol not in data:
        return f"Cryptocurrency '{symbol}' not found. Please check the symbol and try again."
    
    price_info = data[symbol]
    
    # Format the response
    result = f"Price Information for {symbol.upper()}:\n"
    result += f"Current Price: ${price_info.get('usd', 0):,.2f}\n"
    result += f"Market Cap: ${price_info.get('usd_market_cap', 0):,.0f}\n"
    result += f"24h Volume: ${price_info.get('usd_24h_vol', 0):,.0f}\n"
    result += f"24h Change: {price_info.get('usd_24h_change', 0):+.2f}%"
    
    return result

@mcp.tool()
async def get_top_cryptos(limit: int = 10) -> str:
    """Get top cryptocurrencies by market cap.
    
    Args:
        limit: Number of top cryptocurrencies to return (default: 10, max: 100)
    """
    if limit > 100:
        limit = 100
    
    url = f"{COINGECKO_API_BASE}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
    
    data = await make_coingecko_request(url)
    
    if not data:
        return "Failed to fetch cryptocurrency data. Please try again later."
    
    if not isinstance(data, list):
        return "Unexpected data format received from API."
    
    result = f"Top {len(data)} Cryptocurrencies by Market Cap:\n\n"
    
    for i, crypto in enumerate(data, 1):
        name = crypto.get('name', 'Unknown')
        symbol = crypto.get('symbol', '').upper()
        price = crypto.get('current_price', 0)
        market_cap = crypto.get('market_cap', 0)
        change_24h = crypto.get('price_change_percentage_24h', 0)
        
        result += f"{i}. {name} ({symbol})\n"
        result += f"   Price: ${price:,.2f}\n"
        result += f"   Market Cap: ${market_cap:,.0f}\n"
        result += f"   24h Change: {change_24h:+.2f}%\n\n"
    
    return result.strip()

@mcp.tool()
async def search_crypto(query: str) -> str:
    """Search for cryptocurrencies by name or symbol.
    
    Args:
        query: Search query (name or symbol)
    """
    url = f"{COINGECKO_API_BASE}/search?query={query}"
    
    data = await make_coingecko_request(url)
    
    if not data:
        return f"Failed to search for '{query}'. Please try again later."
    
    coins = data.get('coins', [])
    
    if not coins:
        return f"No cryptocurrencies found matching '{query}'."
    
    result = f"Search Results for '{query}':\n\n"
    
    for i, coin in enumerate(coins[:10], 1):  # Limit to top 10 results
        name = coin.get('name', 'Unknown')
        symbol = coin.get('symbol', '').upper()
        market_cap_rank = coin.get('market_cap_rank', 'N/A')
        
        result += f"{i}. {name} ({symbol})\n"
        result += f"   Market Cap Rank: #{market_cap_rank}\n"
        result += f"   ID: {coin.get('id', 'Unknown')}\n\n"
    
    if len(coins) > 10:
        result += f"... and {len(coins) - 10} more results"
    
    return result.strip()

@mcp.tool()
async def get_crypto_trending() -> str:
    """Get trending cryptocurrencies.
    
    Returns:
        List of trending cryptocurrencies
    """
    url = f"{COINGECKO_API_BASE}/search/trending"
    
    data = await make_coingecko_request(url)
    
    if not data:
        return "Failed to fetch trending cryptocurrencies. Please try again later."
    
    trending_coins = data.get('coins', [])
    
    if not trending_coins:
        return "No trending cryptocurrencies found."
    
    result = "🔥 Trending Cryptocurrencies:\n\n"
    
    for i, item in enumerate(trending_coins, 1):
        coin = item.get('item', {})
        name = coin.get('name', 'Unknown')
        symbol = coin.get('symbol', '').upper()
        market_cap_rank = coin.get('market_cap_rank', 'N/A')
        
        result += f"{i}. {name} ({symbol})\n"
        result += f"   Market Cap Rank: #{market_cap_rank}\n"
        result += f"   ID: {coin.get('id', 'Unknown')}\n\n"
    
    return result.strip()

@mcp.tool()
async def get_crypto_fear_greed() -> str:
    """Get the current Crypto Fear & Greed Index.
    
    Returns:
        Current fear and greed index value and interpretation
    """
    url = f"{COINGECKO_API_BASE}/fear_greed_index"
    
    data = await make_coingecko_request(url)
    
    if not data:
        return "Failed to fetch Fear & Greed Index. Please try again later."
    
    # The API might return different structures, so we'll handle it gracefully
    if isinstance(data, list) and len(data) > 0:
        latest_data = data[0]
    elif isinstance(data, dict):
        latest_data = data
    else:
        return "Unexpected data format for Fear & Greed Index."
    
    value = latest_data.get('value', 'Unknown')
    timestamp = latest_data.get('timestamp', 'Unknown')
    
    # Interpret the value
    if isinstance(value, (int, float)):
        if value <= 25:
            sentiment = "Extreme Fear"
            emoji = "😰"
        elif value <= 45:
            sentiment = "Fear"
            emoji = "😟"
        elif value <= 55:
            sentiment = "Neutral"
            emoji = "😐"
        elif value <= 75:
            sentiment = "Greed"
            emoji = "😊"
        else:
            sentiment = "Extreme Greed"
            emoji = "🚀"
    else:
        sentiment = "Unknown"
        emoji = "❓"
    
    result = f"📊 Crypto Fear & Greed Index\n\n"
    result += f"Current Value: {value}\n"
    result += f"Sentiment: {emoji} {sentiment}\n"
    result += f"Last Updated: {timestamp}"
    
    return result

@mcp.resource("crypto://{symbol}")
def crypto_resource(symbol: str) -> str:
    """Access cryptocurrency resources"""
    return f"Crypto resource: {symbol.upper()}"

if __name__ == "__main__":
    # Run the server
    import asyncio
    asyncio.run(mcp.run())
