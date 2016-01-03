package com.forter;


import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.base.Throwables;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class JavaShellBolt {
    public static void main(String[] args) throws IOException, InterruptedException {
        ObjectMapper mapper = new ObjectMapper();

        BufferedReader stream = new BufferedReader(new InputStreamReader(System.in), 1024*1024);

        String line;
        while( (line = stream.readLine()) != null ) {
            JsonNode object;
            try {
                if (line.equals("end"))
                    continue;
                object = mapper.readTree(line);
            } catch (IOException e) {
                throw Throwables.propagate(e);
            }

            System.out.println(mapper.writeValueAsString(object));
        }
    }
}
