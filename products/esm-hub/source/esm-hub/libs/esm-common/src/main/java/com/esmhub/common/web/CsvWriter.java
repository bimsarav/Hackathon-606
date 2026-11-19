package com.esmhub.common.web;

import java.nio.charset.StandardCharsets;
import java.util.List;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

/** CSV export that neutralises spreadsheet formula injection (cells starting = + - @ tab CR get a leading quote). */
public final class CsvWriter {
    private CsvWriter() {}

    public static String cell(Object v) {
        String s = v == null ? "" : String.valueOf(v);
        if (!s.isEmpty() && "=+-@\t\r".indexOf(s.charAt(0)) >= 0) {
            s = "'" + s;
        }
        if (s.contains(",") || s.contains("\"") || s.contains("\n") || s.contains("\r")) {
            s = "\"" + s.replace("\"", "\"\"") + "\"";
        }
        return s;
    }

    public static ResponseEntity<byte[]> response(String filename, List<String> header, List<List<?>> rows) {
        StringBuilder sb = new StringBuilder();
        sb.append(String.join(",", header.stream().map(CsvWriter::cell).toList())).append("\r\n");
        for (List<?> row : rows) {
            sb.append(String.join(",", row.stream().map(CsvWriter::cell).toList())).append("\r\n");
        }
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .contentType(new MediaType("text", "csv", StandardCharsets.UTF_8))
                .body(sb.toString().getBytes(StandardCharsets.UTF_8));
    }
}
