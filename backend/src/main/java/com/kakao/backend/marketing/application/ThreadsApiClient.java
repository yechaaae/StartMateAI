package com.kakao.backend.marketing.application;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

@Component
@RequiredArgsConstructor
public class ThreadsApiClient {

    private static final String GRAPH_BASE_URL = "https://graph.threads.net/v1.0";
    private static final String TOKEN_URL = "https://graph.threads.net/oauth/access_token";

    private final ObjectMapper objectMapper;

    @Value("${meta.threads.app-id:${META_APP_ID:}}")
    private String appId;

    @Value("${meta.threads.app-secret:${META_APP_SECRET:}}")
    private String appSecret;

    @Value("${meta.threads.redirect-uri:${META_REDIRECT_URI:http://localhost:8080/api/sns/threads/callback}}")
    private String redirectUri;

    private final RestClient restClient = RestClient.create();

    public String buildAuthorizeUrl(String state) {
        requireMetaConfig();
        Map<String, String> params = new LinkedHashMap<>();
        params.put("client_id", appId);
        params.put("redirect_uri", redirectUri);
        params.put("scope", "threads_basic,threads_content_publish");
        params.put("response_type", "code");
        params.put("state", state);
        return "https://threads.net/oauth/authorize?" + formEncode(params);
    }

    public ThreadsToken exchangeCode(String code) {
        requireMetaConfig();
        Map<String, String> params = new LinkedHashMap<>();
        params.put("client_id", appId);
        params.put("client_secret", appSecret);
        params.put("grant_type", "authorization_code");
        params.put("redirect_uri", redirectUri);
        params.put("code", code);

        JsonNode body = postForm(TOKEN_URL, params, null);
        String accessToken = requiredText(body, "access_token");
        String userId = requiredText(body, "user_id");
        long expiresIn = body.path("expires_in").asLong(3600);

        return new ThreadsToken(
                accessToken,
                userId,
                LocalDateTime.now().plusSeconds(Math.max(expiresIn, 60))
        );
    }

    public ThreadsProfile loadProfile(String accessToken) {
        URI uri = URI.create(GRAPH_BASE_URL + "/me?fields=id,username");
        JsonNode body = parseJson(restClient.get()
                .uri(uri)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken)
                .retrieve()
                .body(String.class));

        return new ThreadsProfile(
                requiredText(body, "id"),
                body.path("username").asText("")
        );
    }

    public String createTextContainer(String threadsUserId, String accessToken, String text) {
        Map<String, String> params = new LinkedHashMap<>();
        params.put("media_type", "TEXT");
        params.put("text", text);
        JsonNode body = postForm(GRAPH_BASE_URL + "/" + threadsUserId + "/threads", params, accessToken);
        return requiredText(body, "id");
    }

    public String publishContainer(String threadsUserId, String accessToken, String creationId) {
        Map<String, String> params = new LinkedHashMap<>();
        params.put("creation_id", creationId);
        JsonNode body = postForm(GRAPH_BASE_URL + "/" + threadsUserId + "/threads_publish", params, accessToken);
        return requiredText(body, "id");
    }

    private JsonNode postForm(String url, Map<String, String> params, String accessToken) {
        RestClient.RequestBodySpec request = restClient.post()
                .uri(URI.create(url))
                .contentType(MediaType.APPLICATION_FORM_URLENCODED);

        if (accessToken != null && !accessToken.isBlank()) {
            request.header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken);
        }

        try {
            return parseJson(request.body(formEncode(params))
                    .retrieve()
                    .body(String.class));
        } catch (RestClientResponseException exception) {
            throw new IllegalStateException(
                    "Threads API request failed: HTTP " + exception.getStatusCode().value()
                            + " / " + exception.getResponseBodyAsString(),
                    exception
            );
        }
    }

    private JsonNode parseJson(String body) {
        try {
            return objectMapper.readTree(body);
        } catch (Exception exception) {
            throw new IllegalStateException("Threads API response was not valid JSON: " + body, exception);
        }
    }

    private String formEncode(Map<String, String> params) {
        return params.entrySet().stream()
                .map(entry -> encode(entry.getKey()) + "=" + encode(entry.getValue()))
                .reduce((left, right) -> left + "&" + right)
                .orElse("");
    }

    private String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    private String requiredText(JsonNode node, String fieldName) {
        if (node == null || node.path(fieldName).isMissingNode() || node.path(fieldName).asText().isBlank()) {
            throw new IllegalStateException("Threads API response missing field: " + fieldName
                    + " / " + safeJson(node));
        }
        return node.path(fieldName).asText();
    }

    private String safeJson(JsonNode node) {
        try {
            return objectMapper.writeValueAsString(node);
        } catch (Exception exception) {
            return String.valueOf(node);
        }
    }

    private void requireMetaConfig() {
        if (appId == null || appId.isBlank() || appSecret == null || appSecret.isBlank()) {
            throw new IllegalStateException("META_APP_ID and META_APP_SECRET are required.");
        }
    }

    public record ThreadsToken(String accessToken, String userId, LocalDateTime expiresAt) {
    }

    public record ThreadsProfile(String id, String username) {
    }
}
