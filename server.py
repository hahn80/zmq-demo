import os
import json
import logging
import uuid
import threading
import zmq

# Define the desired date format
date_format = "%b %d, %Y %I:%M:%S %p"

# Define the log message format including script name and a newline character
script_name = os.path.basename(__file__)
log_format = f"%(asctime)s {script_name}\n%(levelname)s: %(message)s"

# Configure the logging module with the formats
logging.basicConfig(level=logging.INFO, format=log_format, datefmt=date_format)

logger = logging.getLogger(__name__)


class Server(threading.Thread):
    def __init__(self):
        self._stop = threading.Event()
        threading.Thread.__init__(self)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.is_set()

    def run(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        # frontend will communicate with client through tcp protocol
        frontend.bind("tcp://*:5576")

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
                    logger.info(f"Receiving a request from << {ticket.decode()}")

                    # Decode the JSON message
                    json_msg = json.loads(msg.decode("utf-8"))

                    handler = RequestHandler(context, ticket, json_msg)
                    handler.start()

            if backend in sockets:
                if sockets[backend] == zmq.POLLIN:
                    ticket = backend.recv()
                    msg = backend.recv()
                    logger.info(f"Sending message back to >> {ticket.decode()}")
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
        payload = self.msg.get("payload", "")
        response = {"predict": "Processed " + payload}

        return response

    def run(self):
        # Simulate a long-running operation
        output = self.process()

        # Worker will send the reply back to the DEALER backend socket via inproc
        worker = self.context.socket(zmq.DEALER)
        worker.connect("inproc://tbrane_endpoint")

        worker.send(self.ticket, zmq.SNDMORE)
        worker.send(json.dumps(output).encode())

        worker.close()


def main():
    # Start the server that will handle incoming requests
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Interrupt received, stopping server...")
        server.stop()
        server.join()
        logger.info("Server has been stopped")


if __name__ == "__main__":
    main()
