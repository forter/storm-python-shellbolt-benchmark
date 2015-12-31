package com.forter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.common.base.Throwables;
import com.google.common.io.Resources;
import org.msgpack.MessagePack;

import java.io.*;
import java.net.URL;
import java.nio.charset.Charset;
import java.text.DecimalFormat;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class ShellBoltBenchmarkApp {
    public static void main(String[] args) throws IOException, InterruptedException {
        URL resource = Resources.getResource("shell_log.json");

        List<String> lines = Resources.readLines(resource, Charset.defaultCharset());

        final String connect = lines.get(0).trim();
        final String tup = lines.get(1).trim();
        final String taskIds = lines.get(2).trim();

        final FileOutputStream outStream = new FileOutputStream(FileDescriptor.out);

        if (args.length == 0 || !args[0].equals("msgpack")) {
            floodStream(outStream, new byte[][]{
                    (connect + "\nend\n").getBytes(),
                    (tup + "\nend\n").getBytes(),
                    (taskIds + "\nend\n").getBytes()
            });
        } else {
            MessagePack msgPack = new MessagePack();
            ObjectMapper mapper = new ObjectMapper();

            ObjectNode node = (ObjectNode) mapper.readTree(tup);
            Map tupleMap = mapper.treeToValue(node, Map.class);

            floodStream(outStream, new byte[][]{
                    msgPack.write(getContextMsgpack()),
                    msgPack.write(tupleMap),
                    msgPack.write(new int[] { 5 })
            });
        }
    }

    private static void floodStream(FileOutputStream stream, byte[][] messages) throws IOException, InterruptedException {
        final byte[] connectBytes = messages[0];
        final byte[] tupleBytes = messages[1];
        final byte[] taskIdBytes = messages[2];

        DataOutputStream bufferedStream = new DataOutputStream(new BufferedOutputStream(stream, 1024 * 1024));
        try {
            bufferedStream.write(connectBytes);
            bufferedStream.flush();

            while (true) {
                bufferedStream.write(tupleBytes);
                bufferedStream.flush();

                bufferedStream.write(taskIdBytes);
                bufferedStream.flush();
            }
        } catch (IOException e) {
            throw Throwables.propagate(e);
        }
    }

    private static Map<String, Object> getContextMsgpack() {
        Map<String, Object> setupmsg = new HashMap<String, Object>();
        setupmsg.put("conf", new HashMap<String, Object>());
        setupmsg.put("pidDir", "/tmp");
        Map context_map = new HashMap();
        context_map.put("taskid", 1);
        context_map.put("task->component", "name");
        setupmsg.put("context", context_map);
        return setupmsg;
    }
}
