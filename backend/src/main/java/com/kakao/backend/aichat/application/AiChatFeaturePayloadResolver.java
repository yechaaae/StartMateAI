package com.kakao.backend.aichat.application;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class AiChatFeaturePayloadResolver {

    public Map<String, Object> resolve(
            String targetFeature,
            String currentResultType,
            Long currentResultId,
            Long selectedIdeaId,
            Map<String, Object> currentResult
    ) {
        Map<String, Object> featurePayload = new LinkedHashMap<>();
        putText(featurePayload, "featureKey", normalize(targetFeature));
        putText(featurePayload, "currentResultType", currentResultType);
        putLong(featurePayload, "currentResultId", currentResultId);
        putLong(featurePayload, "selectedIdeaId", selectedIdeaId);

        Map<String, Object> safeCurrentResult = currentResult == null ? Map.of() : currentResult;
        String featureKey = normalize(targetFeature);

        switch (featureKey) {
            case "SUPPORT" -> resolveSupport(featurePayload, safeCurrentResult);
            case "PLAN" -> resolvePlan(featurePayload, safeCurrentResult);
            case "OPERATION" -> resolveOperation(featurePayload, safeCurrentResult);
            case "SNS" -> resolveSns(featurePayload, safeCurrentResult);
            case "ITEM", "SIMULATOR" -> featurePayload.put("selection", safeCurrentResult);
            default -> featurePayload.put("currentResult", safeCurrentResult);
        }

        featurePayload.putIfAbsent("currentResult", safeCurrentResult);
        return featurePayload;
    }

    private void resolveSupport(Map<String, Object> featurePayload, Map<String, Object> currentResult) {
        featurePayload.put("supportContext", mapOf(
                "supportSearchMode", stringOrEmpty(currentResult.get("supportSearchMode")),
                "userGoal", stringOrEmpty(currentResult.get("userGoal"))
        ));
        featurePayload.put("selection", singleEntryMap(
                "selectedSupportProgram", mapOrEmpty(currentResult.get("selectedSupportProgram"))
        ));
        featurePayload.put("currentResult", currentResult);
    }

    private void resolvePlan(Map<String, Object> featurePayload, Map<String, Object> currentResult) {
        featurePayload.put("planContext", mapOf(
                "planGoal", stringOrEmpty(currentResult.get("planGoal")),
                "focusedSection", mapOrEmpty(currentResult.get("focusedSection"))
        ));
        featurePayload.put("selection", singleEntryMap(
                "selectedSupportProgram", mapOrEmpty(currentResult.get("selectedSupportProgram"))
        ));
        featurePayload.put("currentResult", currentResult);
    }

    private void resolveOperation(Map<String, Object> featurePayload, Map<String, Object> currentResult) {
        featurePayload.put("businessContext", mapOrEmpty(currentResult.get("businessContext")));
        featurePayload.put("operationContext", mapOf(
                "input", mapOrEmpty(currentResult.get("operationInput")),
                "report", mapOrEmpty(currentResult.get("operationReport"))
        ));
        putList(featurePayload, "contextPriority", currentResult.get("contextPriority"));
        featurePayload.put("currentResult", currentResult);
    }

    private void resolveSns(Map<String, Object> featurePayload, Map<String, Object> currentResult) {
        featurePayload.put("campaignContext", mapOrEmpty(currentResult.get("campaignContext")));
        featurePayload.put("campaignDraft", mapOrEmpty(currentResult.get("campaignDraft")));
        putList(featurePayload, "contextPriority", currentResult.get("contextPriority"));
        featurePayload.put("currentResult", currentResult);
    }

    private Map<String, Object> mapOf(String key1, Object value1, String key2, Object value2) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put(key1, value1);
        values.put(key2, value2);
        return values;
    }

    private Map<String, Object> singleEntryMap(String key, Object value) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put(key, value);
        return values;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapOrEmpty(Object value) {
        if (value instanceof Map<?, ?> map) {
            return new LinkedHashMap<>((Map<String, Object>) map);
        }
        return Map.of();
    }

    private String stringOrEmpty(Object value) {
        if (value == null) {
            return "";
        }
        String text = String.valueOf(value);
        return text.isBlank() ? "" : text;
    }

    private void putText(Map<String, Object> target, String key, String value) {
        if (value != null && !value.isBlank()) {
            target.put(key, value);
        }
    }

    private void putLong(Map<String, Object> target, String key, Long value) {
        if (value != null) {
            target.put(key, value);
        }
    }

    private void putList(Map<String, Object> target, String key, Object value) {
        if (value instanceof List<?> list && !list.isEmpty()) {
            target.put(key, list);
        }
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toUpperCase();
    }
}
