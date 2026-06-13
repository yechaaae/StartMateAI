package com.kakao.backend.aichat.application;

import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import com.kakao.backend.commercialarea.service.CommercialAreaService;
import com.kakao.backend.policy.dto.RecommendedProgramResponse;
import com.kakao.backend.policy.dto.SupportProgramRecommendationRequest;
import com.kakao.backend.policy.service.SupportProgramService;
import com.kakao.backend.startupProfile.model.StartupProfile;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class AiChatExternalReferenceDataService {

    private static final List<String> SUPPORT_KEYWORDS = List.of("지원사업", "공고", "정책", "사업화", "멘토링", "교육", "창업지원");
    private static final List<String> COMMERCIAL_AREA_KEYWORDS = List.of("상권", "입지", "경쟁", "경쟁점", "주변", "카페", "연남동", "마포구");

    private final SupportProgramService supportProgramService;
    private final CommercialAreaService commercialAreaService;

    public AiChatExternalReferenceDataService(
            SupportProgramService supportProgramService,
            CommercialAreaService commercialAreaService
    ) {
        this.supportProgramService = supportProgramService;
        this.commercialAreaService = commercialAreaService;
    }

    public Map<String, Object> resolve(AiChatDispatchCommand command) {
        if (command == null) {
            return Map.of();
        }

        Map<String, Object> externalData = new LinkedHashMap<>();
        String message = command.message() != null ? command.message().getContent() : "";

        if (shouldAttachSupportPrograms(command, message)) {
            try {
                List<RecommendedProgramResponse> programs = supportProgramService.recommend(
                        toSupportRecommendationRequest(command.startupProfile(), message, command.currentResult())
                );
                if (!programs.isEmpty()) {
                    externalData.put("supportPrograms", supportProgramsPayload(programs));
                }
            } catch (IllegalStateException ignored) {
                // No imported policy data yet; avoid injecting synthetic recommendations as external evidence.
            }
        }

        if (shouldAttachCommercialArea(command, message)) {
            CommercialAreaResponse area = commercialAreaService.analyze(
                    toCommercialAreaRequest(command.startupProfile(), message, command.currentResult())
            );
            externalData.put("commercialArea", commercialAreaPayload(area));
        }

        return externalData;
    }

    private boolean shouldAttachSupportPrograms(AiChatDispatchCommand command, String message) {
        return isFeature(command, "SUPPORT")
                || isIntent(command, "policy")
                || containsAgent(command, "PolicyAgent")
                || containsAny(message, SUPPORT_KEYWORDS);
    }

    private boolean shouldAttachCommercialArea(AiChatDispatchCommand command, String message) {
        return containsAny(message, COMMERCIAL_AREA_KEYWORDS)
                || containsAny(text(command.currentResult()), COMMERCIAL_AREA_KEYWORDS)
                || isFeature(command, "COMMERCIAL_AREA");
    }

    private SupportProgramRecommendationRequest toSupportRecommendationRequest(
            StartupProfile profile,
            String message,
            Map<String, Object> currentResult
    ) {
        String desiredRegion = firstNonBlank(
                textValue(currentResult, "desiredRegion"),
                profile != null ? profile.getBusinessRegion() : null,
                profile != null ? profile.getResidenceRegion() : null,
                message
        );
        String interest = firstNonBlank(
                textValue(currentResult, "industry"),
                textValue(currentResult, "itemName"),
                profile != null ? profile.getInterestField() : null,
                message
        );

        return new SupportProgramRecommendationRequest(
                ageFrom(message),
                sidoFrom(profile != null ? profile.getResidenceRegion() : null),
                sidoFrom(desiredRegion),
                sigunguFrom(desiredRegion),
                "pre_founder",
                false,
                null,
                "idea",
                industryLargeFrom(interest),
                industryMediumFrom(interest),
                industrySmallFrom(interest),
                profile != null && profile.getInitialBudget() != null ? profile.getInitialBudget().longValue() : null,
                List.of("grant", "education", "mentoring", "space")
        );
    }

    private CommercialAreaRequest toCommercialAreaRequest(
            StartupProfile profile,
            String message,
            Map<String, Object> currentResult
    ) {
        String region = firstNonBlank(
                textValue(currentResult, "desiredRegion"),
                textValue(currentResult, "region"),
                profile != null ? profile.getBusinessRegion() : null,
                profile != null ? profile.getResidenceRegion() : null,
                message
        );
        String industry = firstNonBlank(
                textValue(currentResult, "industry"),
                textValue(currentResult, "itemName"),
                profile != null ? profile.getInterestField() : null,
                message
        );

        return new CommercialAreaRequest(
                sidoFrom(region),
                firstNonBlank(sigunguFrom(region), containsAny(message, List.of("마포")) ? "마포구" : null),
                firstNonBlank(dongFrom(region), containsAny(message, List.of("연남")) ? "연남동" : null),
                null,
                null,
                null,
                industryLargeFrom(industry),
                industryMediumFrom(industry),
                industrySmallFrom(industry)
        );
    }

    private Map<String, Object> supportProgramsPayload(List<RecommendedProgramResponse> programs) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("items", programs.stream().limit(5).map(this::supportProgramItem).toList());
        payload.put("generatedAt", LocalDateTime.now().toString());
        payload.put("source", "backend.support_programs");
        return payload;
    }

    private Map<String, Object> supportProgramItem(RecommendedProgramResponse program) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("programId", program.programId());
        item.put("title", program.title());
        item.put("source", program.source());
        item.put("summary", program.summary());
        item.put("regionCondition", program.regionCondition());
        item.put("supportAmount", program.supportAmount());
        item.put("requiredDocuments", program.requiredDocuments());
        item.put("organization", program.organization());
        item.put("supportType", program.supportType());
        item.put("status", program.status());
        item.put("matchScore", program.matchScore());
        item.put("matchReasons", program.matchReasons());
        item.put("cautionReasons", program.cautionReasons());
        item.put("applicationEndDate", program.applicationEndDate() != null ? program.applicationEndDate().toString() : null);
        item.put("applyUrl", program.applyUrl());
        return item;
    }

    private Map<String, Object> commercialAreaPayload(CommercialAreaResponse area) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("areaLabel", area.areaLabel());
        payload.put("industryLabel", area.industryLabel());
        payload.put("totalStores", area.totalStores());
        payload.put("directCompetitors", area.directCompetitors());
        payload.put("similarCompetitors", area.similarCompetitors());
        payload.put("competitionLevel", area.competitionLevel());
        payload.put("notes", area.notes());
        payload.put("generatedAt", LocalDateTime.now().toString());
        payload.put("source", "backend.commercial_area");
        return payload;
    }

    private boolean isFeature(AiChatDispatchCommand command, String feature) {
        return command.room() != null
                && command.room().getTargetFeature() != null
                && feature.equalsIgnoreCase(command.room().getTargetFeature());
    }

    private boolean isIntent(AiChatDispatchCommand command, String intent) {
        return command.intent() != null && intent.equalsIgnoreCase(command.intent());
    }

    private boolean containsAgent(AiChatDispatchCommand command, String agent) {
        return command.candidateAgents() != null && command.candidateAgents().stream().anyMatch(agent::equalsIgnoreCase);
    }

    private boolean containsAny(String raw, List<String> keywords) {
        String value = lower(raw);
        return keywords.stream().anyMatch(keyword -> value.contains(lower(keyword)));
    }

    private String industryLargeFrom(String raw) {
        return containsAny(raw, List.of("카페", "커피", "음식", "식당", "디저트")) ? "음식점업" : null;
    }

    private String industryMediumFrom(String raw) {
        return containsAny(raw, List.of("카페", "커피")) ? "커피점/카페" : null;
    }

    private String industrySmallFrom(String raw) {
        return containsAny(raw, List.of("카페", "커피")) ? "카페" : null;
    }

    private Integer ageFrom(String raw) {
        List<Integer> numbers = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        for (char ch : raw.toCharArray()) {
            if (Character.isDigit(ch)) {
                current.append(ch);
            } else if (!current.isEmpty()) {
                numbers.add(Integer.parseInt(current.toString()));
                current.setLength(0);
            }
        }
        if (!current.isEmpty()) {
            numbers.add(Integer.parseInt(current.toString()));
        }
        return numbers.stream()
                .filter(number -> number >= 19 && number <= 80)
                .findFirst()
                .orElse(null);
    }

    private String sidoFrom(String raw) {
        String text = text(raw);
        if (text.contains("서울")) {
            return "서울";
        }
        if (text.contains("부산")) {
            return "부산";
        }
        if (text.contains("대구")) {
            return "대구";
        }
        if (text.contains("인천")) {
            return "인천";
        }
        if (text.contains("광주")) {
            return "광주";
        }
        if (text.contains("대전")) {
            return "대전";
        }
        if (text.contains("울산")) {
            return "울산";
        }
        if (text.contains("세종")) {
            return "세종";
        }
        return tokenEndingWith(text, List.of("도", "시"));
    }

    private String sigunguFrom(String raw) {
        String text = text(raw);
        if (text.contains("마포")) {
            return "마포구";
        }
        return tokenEndingWith(text, List.of("구", "군"));
    }

    private String dongFrom(String raw) {
        String text = text(raw);
        if (text.contains("연남")) {
            return "연남동";
        }
        return tokenEndingWith(text, List.of("동", "읍", "면"));
    }

    private String tokenEndingWith(String raw, List<String> suffixes) {
        for (String token : text(raw).split("[\\s,/]")) {
            String trimmed = token.trim();
            if (!trimmed.isBlank() && suffixes.stream().anyMatch(trimmed::endsWith)) {
                return trimmed;
            }
        }
        return null;
    }

    private String textValue(Map<String, Object> map, String key) {
        if (map == null || !map.containsKey(key) || map.get(key) == null) {
            return null;
        }
        return String.valueOf(map.get(key));
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String lower(String value) {
        return text(value).toLowerCase(Locale.ROOT);
    }
}
