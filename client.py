import json
import logging
import uuid
import argparse
import zmq

# Define the desired date format
date_format = "%b %d, %Y %I:%M:%S %p"

# Define the log message format including time and script name
log_format = f"%(asctime)s Titan TBrane Client\n%(levelname)s: %(message)s"

# Configure the logging module with the formats
logging.basicConfig(level=logging.INFO, format=log_format, datefmt=date_format)

logger = logging.getLogger(__name__)


def request_zmq(port=5566):
    front_endpoint = f"tcp://localhost:{port}"
    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    ticket = str(uuid.uuid4())
    text = "This has id: " + ticket

    socket.setsockopt_string(zmq.IDENTITY, ticket)
    socket.connect(front_endpoint)
    logger.info(f"Client {ticket} started\n")

    # Create a dictionary object
    obj = {"payload": text, "ticket": ticket}

    # Convert dictionary to JSON string
    json_str = json.dumps(obj)

    # Send JSON string as bytes
    socket.send(json_str.encode("utf-8"))

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while True:
        socks = dict(poller.poll(timeout=1000))
        if socket in socks and socks[socket] == zmq.POLLIN:
            msg = socket.recv()
            # Decode received bytes back to JSON string
            json_response = msg.decode("utf-8")
            response = json.loads(json_response)
            logger.info(response)
            preds = response.get("predict")
            logger.info(preds)
            break  # Exit the loop once a reply is received

    socket.disconnect(front_endpoint)
    socket.close()
    context.term()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TBrane Server")
    parser.add_argument(
        "--port",
        type=int,
        required=False,
        default=5566,
        help="Port number to bind the server to",
    )
    args = parser.parse_args()
    request_zmq(port=args.port)
