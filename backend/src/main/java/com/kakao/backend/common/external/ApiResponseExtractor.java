package com.kakao.backend.common.external;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class ApiResponseExtractor {

    private final ObjectMapper objectMapper;

    public ApiResponseExtractor(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public List<Map<String, Object>> extractItems(String body) {
        if (body == null || body.isBlank()) {
            return List.of();
        }
        try {
            Object root = objectMapper.readValue(body, Object.class);
            List<Map<String, Object>> items = new ArrayList<>();
            collectItems(root, items);
            return items;
        } catch (Exception ignored) {
            return List.of();
        }
    }

    @SuppressWarnings("unchecked")
    private void collectItems(Object value, List<Map<String, Object>> items) {
        if (value instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    items.add(objectMapper.convertValue(map, new TypeReference<Map<String, Object>>() {
                    }));
                } else {
                    collectItems(item, items);
                }
            }
            return;
        }

        if (!(value instanceof Map<?, ?> map)) {
            return;
        }

        Object direct = firstPresent((Map<String, Object>) map, "item", "items", "data", "result", "youthPolicyList", "policyList");
        if (direct instanceof List<?> || direct instanceof Map<?, ?>) {
            collectItems(direct, items);
            if (!items.isEmpty()) {
                return;
            }
        }

        for (Object child : map.values()) {
            collectItems(child, items);
            if (!items.isEmpty()) {
                return;
            }
        }

        if (!map.isEmpty()) {
            items.add(objectMapper.convertValue(map, new TypeReference<Map<String, Object>>() {
            }));
        }
    }

    private Object firstPresent(Map<String, Object> map, String... keys) {
        for (String key : keys) {
            if (map.containsKey(key)) {
                return map.get(key);
            }
        }
        return null;
    }
}
