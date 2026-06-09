package com.kakao.backend.common.external;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ExternalApiClient {

    private final HttpClient httpClient;
    private final int retries;
    private final int timeoutMs;

    public ExternalApiClient(
            @Value("${startmate.external-api.retries:3}") int retries,
            @Value("${startmate.external-api.timeout-ms:15000}") int timeoutMs
    ) {
        this.retries = Math.max(1, retries);
        this.timeoutMs = Math.max(500, timeoutMs);
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(this.timeoutMs))
                .build();
    }

    public ExternalApiResult get(String url, Map<String, String> params) {
        String requestUrl = appendQuery(url, params);
        for (int attempt = 1; attempt <= retries; attempt++) {
            try {
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(requestUrl))
                        .timeout(Duration.ofMillis(timeoutMs))
                        .GET()
                        .build();
                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
                if (response.statusCode() >= 200 && response.statusCode() < 300) {
                    return ExternalApiResult.ok(requestUrl, response.body(), response.statusCode());
                }
                if (attempt == retries) {
                    return ExternalApiResult.fail(requestUrl, response.statusCode(), "HTTP " + response.statusCode());
                }
            } catch (IOException | InterruptedException | IllegalArgumentException error) {
                if (error instanceof InterruptedException) {
                    Thread.currentThread().interrupt();
                }
                if (attempt == retries) {
                    return ExternalApiResult.fail(requestUrl, null, error.getMessage());
                }
            }
        }
        return ExternalApiResult.fail(requestUrl, null, "Unexpected fetch failure");
    }

    private String appendQuery(String url, Map<String, String> params) {
        String query = params.entrySet().stream()
                .filter(entry -> entry.getValue() != null && !entry.getValue().isBlank())
                .map(entry -> encode(entry.getKey()) + "=" + encode(entry.getValue()))
                .collect(Collectors.joining("&"));
        if (query.isBlank()) {
            return url;
        }
        return url + (url.contains("?") ? "&" : "?") + query;
    }

    private String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }
}
