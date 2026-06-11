package com.kakao.backend.commercialarea.connector;

import com.kakao.backend.common.external.ApiResponseExtractor;
import com.kakao.backend.common.external.ExternalApiClient;
import com.kakao.backend.common.external.ExternalApiResult;
import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class CommercialStoreApiConnector {

    private final ExternalApiClient apiClient;
    private final ApiResponseExtractor extractor;
    private final String endpoint;
    private final String serviceKey;

    public CommercialStoreApiConnector(
            ExternalApiClient apiClient,
            ApiResponseExtractor extractor,
            @Value("${startmate.external-api.commercial-store-radius-url:https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInRadius}") String endpoint,
            @Value("${DATA_GO_KR_SERVICE_KEY:}") String serviceKey
    ) {
        this.apiClient = apiClient;
        this.extractor = extractor;
        this.endpoint = endpoint;
        this.serviceKey = serviceKey;
    }

    public List<Map<String, Object>> fetchStoresInRadius(CommercialAreaRequest request) {
        if (serviceKey == null || serviceKey.isBlank()
                || request.latitude() == null
                || request.longitude() == null) {
            return List.of();
        }

        Map<String, String> params = new LinkedHashMap<>();
        params.put("serviceKey", serviceKey);
        params.put("type", "json");
        params.put("pageNo", "1");
        params.put("numOfRows", "1000");
        params.put("cx", String.valueOf(request.longitude()));
        params.put("cy", String.valueOf(request.latitude()));
        params.put("radius", String.valueOf(normalizeRadius(request.radiusMeters())));

        ExternalApiResult result = apiClient.get(endpoint, params);
        return result.ok() ? extractor.extractItems(result.body()) : List.of();
    }

    private int normalizeRadius(Integer radiusMeters) {
        if (radiusMeters == null || radiusMeters <= 0) {
            return 500;
        }
        return Math.min(radiusMeters, 2000);
    }
}
