import json
import logging
import threading
import uuid
import argparse
import zmq


# Define the desired date format
date_format = "%b %d, %Y %I:%M:%S %p"

# Define the log message format including time and script name
log_format = f"%(asctime)s Titan TBrane Server\n%(levelname)s: %(message)s"

# Configure the logging module with the formats
logging.basicConfig(level=logging.INFO, format=log_format, datefmt=date_format)

logger = logging.getLogger(__name__)


def is_valid_uuid(ticket):
    try:
        txt = ticket.decode("utf-8", "ignore")
        uuid.UUID(txt)
        return True
    except ValueError:
        return False


class Server(threading.Thread):
    def __init__(self, ip="127.0.0.1", port=5566):
        self.event = threading.Event()
        self.port = port
        self.ip = ip
        threading.Thread.__init__(self)

    def stop(self):
        self.event.set()

    def stopped(self):
        return self.event.is_set()

    def run(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        # frontend will communicate with client through tcp protocol
        frontend.bind(f"tcp://{self.ip}:{self.port}")

        # backend and frontend work internally
        backend = context.socket(zmq.DEALER)
        backend.bind("inproc://tbrane_endpoint")

        poll = zmq.Poller()
        poll.register(frontend, zmq.POLLIN)
        poll.register(backend, zmq.POLLIN)

        while not self.stopped():
            sockets = dict(poll.poll())
            if frontend in sockets:
                if sockets[frontend] == zmq.POLLIN:
                    ticket, _, msg = frontend.recv_multipart()
                    logger.info(f"Receiving a request from << {ticket}")

                    handler = RequestHandler(context, ticket, msg)
                    handler.start()

            if backend in sockets:
                # backend received result from worker and now transfers to frontend
                if sockets[backend] == zmq.POLLIN:
                    ticket = backend.recv()
                    msg = backend.recv()
                    logger.info(f"Sending message back to >> {ticket}")
                    frontend.send_multipart([ticket, b"", msg])

        frontend.close()
        backend.close()
        context.term()


class RequestHandler(threading.Thread):
    def __init__(self, context, ticket, msg):
        threading.Thread.__init__(self)
        self.context = context
        self.msg = msg
        self.ticket = ticket

    def process(self):
        # Process the JSON message received
        # Decode the JSON message
        if is_valid_uuid(self.ticket):
            json_msg = json.loads(self.msg.decode("utf-8"))
            payload = json_msg.get("payload", "")
            return {"predict": "Processed " + payload}

        return {"error": "Invalid ticket! Are you alien?"}

    def run(self):
        # Simulate a long-running operation
        output = self.process()

        # Worker is a middle man, it sends result to backend pool
        worker = self.context.socket(zmq.DEALER)
        worker.connect("inproc://tbrane_endpoint")

        worker.send(self.ticket, zmq.SNDMORE)
        worker.send(json.dumps(output).encode())

        worker.close()


def main(port=5566):
    # Start the server that will handle incoming requests
    logger.info(f"The server starting at port: {port}")
    server = Server(port=port)
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Interrupt received, stopping server...")
        server.stop()
        server.join()
        logger.info("Server has been stopped")


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

    main(port=args.port)
