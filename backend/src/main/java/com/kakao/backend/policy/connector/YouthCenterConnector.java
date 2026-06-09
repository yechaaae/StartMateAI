package com.kakao.backend.policy.connector;

import com.kakao.backend.common.external.ApiResponseExtractor;
import com.kakao.backend.common.external.ExternalApiClient;
import com.kakao.backend.common.external.ExternalApiResult;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class YouthCenterConnector {

    private final ExternalApiClient apiClient;
    private final ApiResponseExtractor extractor;
    private final String endpoint;
    private final String apiKey;

    public YouthCenterConnector(
            ExternalApiClient apiClient,
            ApiResponseExtractor extractor,
            @Value("${startmate.external-api.youthcenter-url:https://www.youthcenter.go.kr/opi/youthPlcyList.do}") String endpoint,
            @Value("${YOUTH_CENTER_API_KEY:}") String apiKey
    ) {
        this.apiClient = apiClient;
        this.extractor = extractor;
        this.endpoint = endpoint;
        this.apiKey = apiKey;
    }

    public List<Map<String, Object>> fetchYouthPolicies(Map<String, String> overrides) {
        if (apiKey == null || apiKey.isBlank()) {
            return List.of();
        }
        Map<String, String> params = new LinkedHashMap<>();
        params.put("openApiVlak", apiKey);
        params.put("pageIndex", "1");
        params.put("display", "100");
        params.put("query", "창업");
        params.put("keyword", "창업,청년창업,사업화,창업교육,창업공간,정책자금");
        params.putAll(overrides);
        ExternalApiResult result = apiClient.get(endpoint, params);
        return result.ok() ? extractor.extractItems(result.body()) : List.of();
    }
}
