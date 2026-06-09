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
public class KstartupConnector {

    private final ExternalApiClient apiClient;
    private final ApiResponseExtractor extractor;
    private final String endpoint;
    private final String serviceKey;

    public KstartupConnector(
            ExternalApiClient apiClient,
            ApiResponseExtractor extractor,
            @Value("${startmate.external-api.kstartup-url:https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01}") String endpoint,
            @Value("${DATA_GO_KR_SERVICE_KEY:}") String serviceKey
    ) {
        this.apiClient = apiClient;
        this.extractor = extractor;
        this.endpoint = endpoint;
        this.serviceKey = serviceKey;
    }

    public List<Map<String, Object>> fetchKstartupAnnouncements(Map<String, String> overrides) {
        if (serviceKey == null || serviceKey.isBlank()) {
            return List.of();
        }
        Map<String, String> params = new LinkedHashMap<>();
        params.put("serviceKey", serviceKey);
        params.put("returnType", "json");
        params.put("pageNo", "1");
        params.put("numOfRows", "100");
        params.putAll(overrides);
        ExternalApiResult result = apiClient.get(endpoint, params);
        return result.ok() ? extractor.extractItems(result.body()) : List.of();
    }
}
