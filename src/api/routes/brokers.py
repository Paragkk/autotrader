"""
Broker Management API Routes
Handles broker connection and status management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.broker_manager import get_broker_manager

router = APIRouter(prefix="/api/brokers", tags=["brokers"])


# Response Models
class BrokerInfo(BaseModel):
    name: str
    display_name: str
    connected: bool
    paper_trading: bool


class BrokerStatusResponse(BaseModel):
    connected_brokers: list[str]
    available_brokers: list[BrokerInfo]


class BrokerConnectionResponse(BaseModel):
    success: bool
    message: str
    broker_name: str = None


@router.get("/status", response_model=BrokerStatusResponse)
async def get_broker_status():
    """
    Get broker connection status

    Returns information about all connected and available brokers.
    """
    try:
        broker_manager = get_broker_manager()

        # Get connected brokers
        connected_brokers = broker_manager.get_connected_brokers()

        # Get all available brokers
        available_brokers = broker_manager.get_available_brokers()

        broker_list = [
            BrokerInfo(
                name=broker["name"],
                display_name=broker["display_name"],
                connected=broker["connected"],
                paper_trading=broker["paper_trading"],
            )
            for broker in available_brokers
        ]

        return BrokerStatusResponse(connected_brokers=connected_brokers, available_brokers=broker_list)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get broker status: {e!s}")


@router.post("/connect/{broker_name}", response_model=BrokerConnectionResponse)
async def connect_broker(broker_name: str):
    """
    Connect to a specific broker

    Connects to the specified broker. If another broker is connected, it will be disconnected first.
    Only one broker can be active at a time.
    """
    try:
        broker_manager = get_broker_manager()

        # Check if already connected to this broker
        if broker_manager.get_active_broker_name() == broker_name:
            return BrokerConnectionResponse(
                success=True,
                message=f"Already connected to {broker_name}",
                broker_name=broker_name,
            )

        # Attempt to connect to the broker (will disconnect current one if any)
        success = await broker_manager.connect_broker(broker_name)

        if success:
            return BrokerConnectionResponse(
                success=True,
                message=f"Successfully connected to {broker_name} (now active broker)",
                broker_name=broker_name,
            )
        return BrokerConnectionResponse(
            success=False,
            message=f"Failed to connect to {broker_name}. Check credentials and configuration.",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to broker: {e!s}")


@router.post("/disconnect/{broker_name}", response_model=BrokerConnectionResponse)
async def disconnect_broker(broker_name: str):
    """
    Disconnect from the active broker

    Disconnects from the active broker if it matches the specified broker name.
    """
    try:
        broker_manager = get_broker_manager()

        active_broker_name = broker_manager.get_active_broker_name()
        if not active_broker_name:
            return BrokerConnectionResponse(success=False, message="No broker is currently connected")

        if active_broker_name != broker_name:
            return BrokerConnectionResponse(
                success=False,
                message=f"Broker {broker_name} is not the active broker. Active broker is {active_broker_name}",
            )

        await broker_manager.disconnect_broker()

        return BrokerConnectionResponse(
            success=True,
            message=f"Disconnected from {broker_name}",
            broker_name=broker_name,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect broker: {e!s}")


@router.post("/disconnect-all", response_model=BrokerConnectionResponse)
async def disconnect_all_brokers():
    """
    Disconnect from the active broker
    """
    try:
        broker_manager = get_broker_manager()

        active_broker_name = broker_manager.get_active_broker_name()
        if not active_broker_name:
            return BrokerConnectionResponse(success=False, message="No broker is currently connected")

        await broker_manager.disconnect_all_brokers()

        return BrokerConnectionResponse(
            success=True,
            message=f"Disconnected from active broker: {active_broker_name}",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect all brokers: {e!s}")


@router.get("/available", response_model=list[BrokerInfo])
async def get_available_brokers():
    """
    Get list of available brokers

    Returns all brokers configured in the system with their current status.
    """
    try:
        broker_manager = get_broker_manager()
        available_brokers = broker_manager.get_available_brokers()

        return [
            BrokerInfo(
                name=broker["name"],
                display_name=broker["display_name"],
                connected=broker["connected"],
                paper_trading=broker["paper_trading"],
            )
            for broker in available_brokers
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available brokers: {e!s}")


@router.get("/connected", response_model=list[BrokerInfo])
async def get_connected_brokers():
    """
    Get the currently active broker

    Returns detailed information about the currently active broker (at most one).
    """
    try:
        broker_manager = get_broker_manager()
        connected_brokers_info = broker_manager.get_connected_brokers_info()

        return [
            BrokerInfo(
                name=broker["name"],
                display_name=broker["display_name"],
                connected=broker["connected"],
                paper_trading=broker["paper_trading"],
            )
            for broker in connected_brokers_info
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connected brokers: {e!s}")


@router.get("/connected/names")
async def get_connected_broker_names():
    """
    Get the active broker name

    Returns the name of the currently active broker.
    """
    try:
        broker_manager = get_broker_manager()
        connected_brokers = broker_manager.get_connected_brokers()

        return {"connected_brokers": connected_brokers}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connected broker names: {e!s}")


@router.get("/active")
async def get_active_broker():
    """
    Get the active broker information

    Returns information about the currently active broker.
    """
    try:
        broker_manager = get_broker_manager()
        active_broker_name = broker_manager.get_active_broker_name()

        if not active_broker_name:
            return {"active_broker": None, "message": "No broker is currently active"}

        # Get broker info
        available_brokers = broker_manager.get_available_brokers()
        active_broker_info = next((b for b in available_brokers if b["name"] == active_broker_name), None)

        return {
            "active_broker": active_broker_info,
            "message": f"{active_broker_name} is currently active",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active broker: {e!s}")
