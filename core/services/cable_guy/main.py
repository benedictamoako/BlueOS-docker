#! /usr/bin/env python3
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, List

from commonwealth.utils.apis import GenericErrorHandlingRoute, PrettyJSONResponse
from commonwealth.utils.decorators import temporary_cache
from commonwealth.utils.logs import InterceptHandler, init_logger
from fastapi import Body, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_versioning import VersionedFastAPI, version
from loguru import logger
from uvicorn import Config, Server

from api.manager import (
    AddressMode,
    EthernetInterface,
    EthernetManager,
    InterfaceAddress,
)

SERVICE_NAME = "cable-guy"

parser = argparse.ArgumentParser(description="CableGuy service for Blue Robotics BlueOS")
parser.add_argument(
    "--default_config",
    dest="default_config",
    type=str,
    default="bluerov2",
    choices=["bluerov2"],
    help="Specify configuration to use if settings file cannot be loaded or is not found. Defaults to 'bluerov2'.",
)

args = parser.parse_args()

if args.default_config == "bluerov2":
    default_configs = [
        EthernetInterface(name="eth0", addresses=[InterfaceAddress(ip="192.168.2.2", mode=AddressMode.Unmanaged)]),
        EthernetInterface(name="usb0", addresses=[InterfaceAddress(ip="192.168.3.1", mode=AddressMode.Server)]),
    ]

manager = EthernetManager(default_configs)

logging.basicConfig(handlers=[InterceptHandler()], level=0)
init_logger(SERVICE_NAME)

HTML_FOLDER = Path.joinpath(Path(__file__).parent.absolute(), "html")

app = FastAPI(
    title="Cable Guy API",
    description="Cable Guy is responsible for managing internet interfaces on BlueOS.",
    default_response_class=PrettyJSONResponse,
    debug=True,
)
app.router.route_class = GenericErrorHandlingRoute


@app.get("/ethernet", response_model=List[EthernetInterface], summary="Retrieve ethernet interfaces.")
@version(1, 0)
@temporary_cache(timeout_seconds=10)
def retrieve_interfaces() -> Any:
    """REST API endpoint to retrieve the configured ethernet interfaces."""
    return manager.get_interfaces()


@app.post("/ethernet", response_model=EthernetInterface, summary="Configure a ethernet interface.")
@version(1, 0)
def configure_interface(interface: EthernetInterface = Body(...)) -> Any:
    """REST API endpoint to configure a new ethernet interface or modify an existing one."""
    manager.set_configuration(interface)
    manager.save()
    return interface


@app.post("/address", summary="Add IP address to interface.")
@version(1, 0)
def add_address(interface_name: str, ip_address: str) -> Any:
    """REST API endpoint to add a static IP address to an ethernet interface."""
    manager.add_static_ip(interface_name, ip_address)
    manager.save()


@app.delete("/address", summary="Delete IP address from interface.")
@version(1, 0)
def delete_address(interface_name: str, ip_address: str) -> Any:
    """REST API endpoint to delete an IP address from an ethernet interface."""
    manager.remove_ip(interface_name, ip_address)
    manager.save()


@app.post("/dhcp", summary="Add local DHCP server to interface.")
@version(1, 0)
def add_dhcp_server(interface_name: str, ipv4_gateway: str) -> Any:
    """REST API endpoint to enable/disable local DHCP server."""
    manager.add_dhcp_server_to_interface(interface_name, ipv4_gateway)
    manager.save()


@app.delete("/dhcp", summary="Remove local DHCP server from interface.")
@version(1, 0)
def remove_dhcp_server(interface_name: str) -> Any:
    """REST API endpoint to enable/disable local DHCP server."""
    manager.remove_dhcp_server_from_interface(interface_name)
    manager.save()


@app.post("/dynamic_ip", summary="Trigger reception of dynamic IP.")
@version(1, 0)
def trigger_dynamic_ip_acquisition(interface_name: str) -> Any:
    """REST API endpoint to trigger interface to receive a new dynamic IP."""
    manager.trigger_dynamic_ip_acquisition(interface_name)
    manager.save()


app = VersionedFastAPI(
    app,
    version="1.0.0",
    prefix_format="/v{major}.{minor}",
    enable_latest=True,
)
app.mount("/", StaticFiles(directory=str(HTML_FOLDER), html=True))

if __name__ == "__main__":
    if os.geteuid() != 0:
        logger.error(
            "You need root privileges to run this script.\nPlease try again, this time using **sudo**. Exiting."
        )
        sys.exit(1)

    loop = asyncio.new_event_loop()

    # # Running uvicorn with log disabled so loguru can handle it
    config = Config(app=app, loop=loop, host="0.0.0.0", port=9090, log_config=None)
    server = Server(config)

    loop.run_until_complete(server.serve())
