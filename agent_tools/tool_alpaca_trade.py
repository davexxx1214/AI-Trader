"""
Alpaca Paper Trading MCP Tools

This module provides MCP tools for executing real trades on Alpaca Paper Trading accounts.
It supports multiple accounts (one per AI model) and synchronizes trades with local position records.

Usage:
    - Each model (gemini, deepseek) has its own Alpaca paper trading account
    - API keys are passed via runtime configuration (ALPACA_API_KEY, ALPACA_SECRET_KEY)
    - Trades are executed on Alpaca AND recorded locally in position.jsonl
"""

import os
import sys
from typing import Any, Dict, Optional

from fastmcp import FastMCP

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import json
from datetime import datetime

from tools.general_tools import get_config_value, write_config_value

# Alpaca imports
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("Warning: alpaca-py not installed. Run: pip install alpaca-py")

mcp = FastMCP("AlpacaTradeTools")


def _get_alpaca_client() -> Optional[TradingClient]:
    """
    Get Alpaca TradingClient using credentials from runtime configuration.
    
    The API keys are set per-model in the runtime config by the scheduler.
    
    Returns:
        TradingClient instance or None if credentials not available
    """
    if not ALPACA_AVAILABLE:
        return None
    
    api_key = get_config_value("ALPACA_API_KEY")
    secret_key = get_config_value("ALPACA_SECRET_KEY")
    
    if not api_key or not secret_key:
        print("Error: ALPACA_API_KEY or ALPACA_SECRET_KEY not set in runtime config")
        return None
    
    # Always use paper=True for paper trading
    return TradingClient(api_key, secret_key, paper=True)


def _record_local_position(
    signature: str,
    today_date: str,
    action: str,
    symbol: str,
    qty: float,
    price: float,
    new_positions: Dict[str, Any]
) -> bool:
    """
    Record trade to local position.jsonl file for tracking.
    
    Args:
        signature: Model signature (e.g., 'gemini-alpaca-live')
        today_date: Trading date/time string
        action: 'buy' or 'sell'
        symbol: Stock symbol
        qty: Quantity traded
        price: Execution price
        new_positions: Updated positions dict
        
    Returns:
        True if recording succeeded
    """
    log_path = get_config_value("LOG_PATH", "./data/agent_data_alpaca")
    if log_path.startswith("./data/"):
        log_path = log_path[7:]  # Remove "./data/" prefix
    
    position_dir = os.path.join(project_root, "data", log_path, signature, "position")
    os.makedirs(position_dir, exist_ok=True)
    position_file_path = os.path.join(position_dir, "position.jsonl")
    
    # Get current action ID
    current_action_id = 0
    if os.path.exists(position_file_path):
        with open(position_file_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        current_action_id = max(current_action_id, record.get("id", 0))
                    except:
                        pass
    
    # Write new record
    record = {
        "date": today_date,
        "id": current_action_id + 1,
        "this_action": {
            "action": action,
            "symbol": symbol,
            "amount": qty,
            "price": price,
            "source": "alpaca"
        },
        "positions": new_positions
    }
    
    with open(position_file_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    
    print(f"Recorded to position.jsonl: {json.dumps(record)}")
    return True


def _get_local_positions(signature: str) -> Dict[str, Any]:
    """
    Get current positions from local position.jsonl file.
    
    Args:
        signature: Model signature
        
    Returns:
        Dictionary of current positions
    """
    log_path = get_config_value("LOG_PATH", "./data/agent_data_alpaca")
    if log_path.startswith("./data/"):
        log_path = log_path[7:]
    
    position_file_path = os.path.join(
        project_root, "data", log_path, signature, "position", "position.jsonl"
    )
    
    if not os.path.exists(position_file_path):
        initial_cash = float(get_config_value("INITIAL_CASH", 10000.0))
        return {"CASH": initial_cash}
    
    # Get latest position record
    latest_positions = {"CASH": 10000.0}
    with open(position_file_path, "r") as f:
        for line in f:
            if line.strip():
                try:
                    record = json.loads(line)
                    if "positions" in record:
                        latest_positions = record["positions"]
                except:
                    pass
    
    return latest_positions


def _init_local_positions(signature: str, initial_cash: float = 10000.0) -> bool:
    """
    Initialize local position file for a new model/signature.
    
    Args:
        signature: Model signature
        initial_cash: Initial cash amount
        
    Returns:
        True if initialization succeeded
    """
    log_path = get_config_value("LOG_PATH", "./data/agent_data_alpaca")
    if log_path.startswith("./data/"):
        log_path = log_path[7:]
    
    position_dir = os.path.join(project_root, "data", log_path, signature, "position")
    os.makedirs(position_dir, exist_ok=True)
    position_file_path = os.path.join(position_dir, "position.jsonl")
    
    if os.path.exists(position_file_path):
        return True  # Already initialized
    
    today_date = get_config_value("TODAY_DATE", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    record = {
        "date": today_date,
        "id": 0,
        "this_action": {"action": "init", "symbol": "CASH", "amount": initial_cash},
        "positions": {"CASH": initial_cash}
    }
    
    with open(position_file_path, "w") as f:
        f.write(json.dumps(record) + "\n")
    
    print(f"Initialized position file for {signature} with ${initial_cash}")
    return True


@mcp.tool()
def buy_alpaca(symbol: str, qty: int) -> Dict[str, Any]:
    """
    Buy stock using Alpaca Paper Trading API.
    
    This function executes a market order on Alpaca and records the trade locally.
    
    Args:
        symbol: Stock symbol (e.g., "AAPL", "MSFT", "SPY")
        qty: Number of shares to buy (must be positive integer)
        
    Returns:
        Dict with order details on success, or error information on failure.
        
    Example:
        >>> result = buy_alpaca("AAPL", 10)
        >>> print(result)  # {"status": "filled", "symbol": "AAPL", "qty": 10, ...}
    """
    signature = get_config_value("SIGNATURE")
    if not signature:
        return {"error": "SIGNATURE not set in runtime config"}
    
    today_date = get_config_value("TODAY_DATE", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Validate qty
    try:
        qty = int(qty)
    except ValueError:
        return {
            "error": f"Invalid quantity. Must be an integer. You provided: {qty}",
            "symbol": symbol,
            "date": today_date
        }
    
    if qty <= 0:
        return {
            "error": f"Quantity must be positive. You tried to buy {qty} shares.",
            "symbol": symbol,
            "qty": qty,
            "date": today_date
        }
    
    # Get Alpaca client
    client = _get_alpaca_client()
    if not client:
        return {
            "error": "Alpaca client not available. Check API credentials.",
            "symbol": symbol,
            "date": today_date
        }
    
    try:
        # Check account buying power first
        account = client.get_account()
        buying_power = float(account.buying_power)
        
        # Create market order
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )
        
        # Submit order
        order = client.submit_order(order_data=order_data)
        
        # Wait briefly for order to fill (market orders usually fill immediately)
        import time
        filled_price = None
        for _ in range(10):  # Wait up to 10 seconds
            time.sleep(1)
            order = client.get_order_by_id(order.id)
            if order.status.value in ["filled", "partially_filled"]:
                filled_price = float(order.filled_avg_price) if order.filled_avg_price else None
                break
            elif order.status.value in ["canceled", "expired", "rejected"]:
                return {
                    "error": f"Order {order.status.value}: {symbol}",
                    "order_id": str(order.id),
                    "symbol": symbol,
                    "qty": qty,
                    "date": today_date
                }
        
        if not filled_price:
            # Order not filled yet, but submitted
            return {
                "status": "pending",
                "order_id": str(order.id),
                "symbol": symbol,
                "qty": qty,
                "message": "Order submitted but not yet filled",
                "date": today_date
            }
        
        # Get updated positions from Alpaca
        alpaca_positions = client.get_all_positions()
        
        # Update local positions
        local_positions = _get_local_positions(signature)
        total_cost = filled_price * qty
        local_positions["CASH"] = local_positions.get("CASH", 0) - total_cost
        local_positions[symbol] = local_positions.get(symbol, 0) + qty
        
        # Record locally
        _record_local_position(
            signature=signature,
            today_date=today_date,
            action="buy",
            symbol=symbol,
            qty=qty,
            price=filled_price,
            new_positions=local_positions
        )
        
        write_config_value("IF_TRADE", True)
        
        return {
            "status": "filled",
            "order_id": str(order.id),
            "symbol": symbol,
            "qty": qty,
            "filled_price": filled_price,
            "total_cost": total_cost,
            "positions": local_positions,
            "date": today_date
        }
        
    except Exception as e:
        return {
            "error": f"Alpaca API error: {str(e)}",
            "symbol": symbol,
            "qty": qty,
            "date": today_date
        }


@mcp.tool()
def sell_alpaca(symbol: str, qty: int) -> Dict[str, Any]:
    """
    Sell stock using Alpaca Paper Trading API.
    
    This function executes a market sell order on Alpaca and records the trade locally.
    
    Args:
        symbol: Stock symbol (e.g., "AAPL", "MSFT", "SPY")
        qty: Number of shares to sell (must be positive integer)
        
    Returns:
        Dict with order details on success, or error information on failure.
        
    Example:
        >>> result = sell_alpaca("AAPL", 5)
        >>> print(result)  # {"status": "filled", "symbol": "AAPL", "qty": 5, ...}
    """
    signature = get_config_value("SIGNATURE")
    if not signature:
        return {"error": "SIGNATURE not set in runtime config"}
    
    today_date = get_config_value("TODAY_DATE", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Validate qty
    try:
        qty = int(qty)
    except ValueError:
        return {
            "error": f"Invalid quantity. Must be an integer. You provided: {qty}",
            "symbol": symbol,
            "date": today_date
        }
    
    if qty <= 0:
        return {
            "error": f"Quantity must be positive. You tried to sell {qty} shares.",
            "symbol": symbol,
            "qty": qty,
            "date": today_date
        }
    
    # Get Alpaca client
    client = _get_alpaca_client()
    if not client:
        return {
            "error": "Alpaca client not available. Check API credentials.",
            "symbol": symbol,
            "date": today_date
        }
    
    try:
        # Check if we have the position
        try:
            position = client.get_open_position(symbol)
            current_qty = int(float(position.qty))
        except Exception:
            return {
                "error": f"No position found for {symbol}. Cannot sell.",
                "symbol": symbol,
                "qty": qty,
                "date": today_date
            }
        
        if current_qty < qty:
            return {
                "error": f"Insufficient shares. Have {current_qty}, want to sell {qty}.",
                "symbol": symbol,
                "have": current_qty,
                "want_to_sell": qty,
                "date": today_date
            }
        
        # Create market sell order
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        
        # Submit order
        order = client.submit_order(order_data=order_data)
        
        # Wait briefly for order to fill
        import time
        filled_price = None
        for _ in range(10):
            time.sleep(1)
            order = client.get_order_by_id(order.id)
            if order.status.value in ["filled", "partially_filled"]:
                filled_price = float(order.filled_avg_price) if order.filled_avg_price else None
                break
            elif order.status.value in ["canceled", "expired", "rejected"]:
                return {
                    "error": f"Order {order.status.value}: {symbol}",
                    "order_id": str(order.id),
                    "symbol": symbol,
                    "qty": qty,
                    "date": today_date
                }
        
        if not filled_price:
            return {
                "status": "pending",
                "order_id": str(order.id),
                "symbol": symbol,
                "qty": qty,
                "message": "Order submitted but not yet filled",
                "date": today_date
            }
        
        # Update local positions
        local_positions = _get_local_positions(signature)
        total_proceeds = filled_price * qty
        local_positions["CASH"] = local_positions.get("CASH", 0) + total_proceeds
        local_positions[symbol] = local_positions.get(symbol, 0) - qty
        
        # Remove position if zero
        if local_positions.get(symbol, 0) <= 0:
            local_positions.pop(symbol, None)
        
        # Record locally
        _record_local_position(
            signature=signature,
            today_date=today_date,
            action="sell",
            symbol=symbol,
            qty=qty,
            price=filled_price,
            new_positions=local_positions
        )
        
        write_config_value("IF_TRADE", True)
        
        return {
            "status": "filled",
            "order_id": str(order.id),
            "symbol": symbol,
            "qty": qty,
            "filled_price": filled_price,
            "total_proceeds": total_proceeds,
            "positions": local_positions,
            "date": today_date
        }
        
    except Exception as e:
        return {
            "error": f"Alpaca API error: {str(e)}",
            "symbol": symbol,
            "qty": qty,
            "date": today_date
        }


@mcp.tool()
def get_alpaca_positions() -> Dict[str, Any]:
    """
    Get all current positions from Alpaca account.
    
    Returns:
        Dict containing all positions with symbol, qty, market_value, etc.
        
    Example:
        >>> positions = get_alpaca_positions()
        >>> print(positions)  # {"AAPL": {"qty": 10, "market_value": 1750.0}, ...}
    """
    client = _get_alpaca_client()
    if not client:
        return {"error": "Alpaca client not available. Check API credentials."}
    
    try:
        positions = client.get_all_positions()
        
        result = {}
        for pos in positions:
            result[pos.symbol] = {
                "qty": float(pos.qty),
                "market_value": float(pos.market_value),
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "unrealized_pl": float(pos.unrealized_pl),
                "unrealized_plpc": float(pos.unrealized_plpc),
                "side": pos.side.value
            }
        
        return {"positions": result, "count": len(result)}
        
    except Exception as e:
        return {"error": f"Failed to get positions: {str(e)}"}


@mcp.tool()
def get_alpaca_account() -> Dict[str, Any]:
    """
    Get Alpaca account information including buying power, equity, etc.
    
    Returns:
        Dict containing account details.
        
    Example:
        >>> account = get_alpaca_account()
        >>> print(account)  # {"buying_power": 10000.0, "equity": 10500.0, ...}
    """
    client = _get_alpaca_client()
    if not client:
        return {"error": "Alpaca client not available. Check API credentials."}
    
    try:
        account = client.get_account()
        
        return {
            "account_number": account.account_number,
            "status": account.status.value,
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "equity": float(account.equity),
            "last_equity": float(account.last_equity),
            "long_market_value": float(account.long_market_value),
            "short_market_value": float(account.short_market_value),
            "initial_margin": float(account.initial_margin),
            "maintenance_margin": float(account.maintenance_margin),
            "daytrade_count": account.daytrade_count,
            "pattern_day_trader": account.pattern_day_trader
        }
        
    except Exception as e:
        return {"error": f"Failed to get account info: {str(e)}"}


@mcp.tool()
def get_alpaca_orders(status: str = "open") -> Dict[str, Any]:
    """
    Get orders from Alpaca account.
    
    Args:
        status: Order status filter - "open", "closed", or "all"
        
    Returns:
        Dict containing list of orders.
        
    Example:
        >>> orders = get_alpaca_orders("open")
        >>> print(orders)  # {"orders": [...], "count": 2}
    """
    client = _get_alpaca_client()
    if not client:
        return {"error": "Alpaca client not available. Check API credentials."}
    
    try:
        # Map status string to enum
        status_map = {
            "open": QueryOrderStatus.OPEN,
            "closed": QueryOrderStatus.CLOSED,
            "all": QueryOrderStatus.ALL
        }
        
        query_status = status_map.get(status.lower(), QueryOrderStatus.OPEN)
        
        request_params = GetOrdersRequest(status=query_status)
        orders = client.get_orders(filter=request_params)
        
        result = []
        for order in orders:
            result.append({
                "id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty) if order.qty else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else None,
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "created_at": str(order.created_at),
                "filled_at": str(order.filled_at) if order.filled_at else None
            })
        
        return {"orders": result, "count": len(result)}
        
    except Exception as e:
        return {"error": f"Failed to get orders: {str(e)}"}


@mcp.tool()
def cancel_alpaca_order(order_id: str) -> Dict[str, Any]:
    """
    Cancel a specific order on Alpaca.
    
    Args:
        order_id: The order ID to cancel
        
    Returns:
        Dict with cancellation status.
    """
    client = _get_alpaca_client()
    if not client:
        return {"error": "Alpaca client not available. Check API credentials."}
    
    try:
        client.cancel_order_by_id(order_id)
        return {"status": "cancelled", "order_id": order_id}
    except Exception as e:
        return {"error": f"Failed to cancel order: {str(e)}", "order_id": order_id}


@mcp.tool()
def sync_positions_from_alpaca() -> Dict[str, Any]:
    """
    Synchronize local position records with actual Alpaca positions.
    
    This is useful when positions may have been modified outside of this tool
    or to reset local state to match Alpaca account.
    
    Returns:
        Dict with synchronized positions.
    """
    signature = get_config_value("SIGNATURE")
    if not signature:
        return {"error": "SIGNATURE not set in runtime config"}
    
    today_date = get_config_value("TODAY_DATE", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    client = _get_alpaca_client()
    if not client:
        return {"error": "Alpaca client not available. Check API credentials."}
    
    try:
        # Get Alpaca account and positions
        account = client.get_account()
        positions = client.get_all_positions()
        
        # Build new positions dict
        new_positions = {
            "CASH": float(account.cash)
        }
        
        for pos in positions:
            new_positions[pos.symbol] = int(float(pos.qty))
        
        # Record sync action
        _record_local_position(
            signature=signature,
            today_date=today_date,
            action="sync",
            symbol="SYNC",
            qty=0,
            price=0,
            new_positions=new_positions
        )
        
        return {
            "status": "synced",
            "positions": new_positions,
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "date": today_date
        }
        
    except Exception as e:
        return {"error": f"Failed to sync positions: {str(e)}"}


if __name__ == "__main__":
    port = int(os.getenv("ALPACA_HTTP_PORT", "8006"))
    mcp.run(transport="streamable-http", port=port)
