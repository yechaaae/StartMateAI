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
public class BizinfoConnector {

    private final ExternalApiClient apiClient;
    private final ApiResponseExtractor extractor;
    private final String endpoint;
    private final String apiKey;

    public BizinfoConnector(
            ExternalApiClient apiClient,
            ApiResponseExtractor extractor,
            @Value("${startmate.external-api.bizinfo-url:https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do}") String endpoint,
            @Value("${BIZINFO_API_KEY:}") String apiKey
    ) {
        this.apiClient = apiClient;
        this.extractor = extractor;
        this.endpoint = endpoint;
        this.apiKey = apiKey;
    }

    public List<Map<String, Object>> fetchBizinfoPrograms(Map<String, String> overrides) {
        if (apiKey == null || apiKey.isBlank()) {
            return List.of();
        }
        Map<String, String> params = new LinkedHashMap<>();
        params.put("crtfcKey", apiKey);
        params.put("dataType", "json");
        params.put("hashtags", "창업,청년");
        params.put("pageUnit", "100");
        params.put("pageIndex", "1");
        params.putAll(overrides);
        ExternalApiResult result = apiClient.get(endpoint, params);
        return result.ok() ? extractor.extractItems(result.body()) : List.of();
    }
}
