import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import org.zeromq.SocketType;
import org.zeromq.ZMQ;
import org.zeromq.ZContext;

import java.lang.reflect.Type;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.logging.Level;
import java.util.logging.Logger;

public class ZmqClient {
    private static final Logger logger = Logger.getLogger(ZmqClient.class.getName());

    public static void main(String[] args) {
        requestZMQ();
    }

    public static void requestZMQ() {
        String frontEndpoint = "tcp://localhost:5566";

        try (ZContext context = new ZContext()) {
            ZMQ.Socket socket = context.createSocket(SocketType.REQ);
            String ticket = UUID.randomUUID().toString();
            String text = "This has id: " + ticket;

            socket.setIdentity(ticket.getBytes(ZMQ.CHARSET));
            socket.connect(frontEndpoint);
            logger.info("Client " + ticket + " started\n");

            // Create a dictionary object
            Map<String, String> obj = new HashMap<>();
            obj.put("payload", text);
            obj.put("ticket", ticket);

            // Convert dictionary to JSON string
            Gson gson = new Gson();
            String jsonStr = gson.toJson(obj);

            // Send JSON string as bytes
            socket.send(jsonStr.getBytes(ZMQ.CHARSET));

            ZMQ.Poller poller = context.createPoller(1);
            poller.register(socket, ZMQ.Poller.POLLIN);

            while (true) {
                if (poller.poll(1000) == -1) {
                    break;
                }

                if (poller.pollin(0)) {
                    byte[] msg = socket.recv();
                    // Decode received bytes back to JSON string
                    String jsonResponse = new String(msg, ZMQ.CHARSET);
                    logger.info(jsonResponse);
                    Type jsonType = new TypeToken<Map<String, Object>>() {}.getType();
                    Map<String, Object> response = gson.fromJson(jsonResponse, jsonType);
                    String preds = (String) response.get("predict");
                    logger.info(preds);
                    break;  // Exit the loop once a reply is received
                }
            }

            socket.disconnect(frontEndpoint);
        } catch (Exception e) {
            logger.log(Level.SEVERE, "An error occurred", e);
        }
    }
}

