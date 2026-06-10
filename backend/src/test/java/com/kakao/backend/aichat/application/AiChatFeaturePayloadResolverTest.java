package com.kakao.backend.aichat.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AiChatFeaturePayloadResolverTest {

    private final AiChatFeaturePayloadResolver resolver = new AiChatFeaturePayloadResolver();

    @Test
    void resolvesSupportFeaturePayloadWithNormalizedSections() {
        Map<String, Object> resolved = resolver.resolve(
                "SUPPORT",
                "SUPPORT_REPORT",
                15L,
                7L,
                Map.of(
                        "supportSearchMode", "PROFILE_IDEA",
                        "userGoal", "HIGH_MATCH",
                        "selectedSupportProgram", Map.of("title", "Youth Startup Fund"),
                        "recommendations", List.of(Map.of("title", "Youth Startup Fund"))
                )
        );

        assertThat(resolved)
                .containsEntry("featureKey", "SUPPORT")
                .containsEntry("currentResultType", "SUPPORT_REPORT")
                .containsEntry("currentResultId", 15L)
                .containsEntry("selectedIdeaId", 7L);

        @SuppressWarnings("unchecked")
        Map<String, Object> supportContext = (Map<String, Object>) resolved.get("supportContext");
        @SuppressWarnings("unchecked")
        Map<String, Object> selection = (Map<String, Object>) resolved.get("selection");

        assertThat(supportContext)
                .containsEntry("supportSearchMode", "PROFILE_IDEA")
                .containsEntry("userGoal", "HIGH_MATCH");
        assertThat(selection)
                .containsEntry("selectedSupportProgram", Map.of("title", "Youth Startup Fund"));
    }

    @Test
    void resolvesOperationFeaturePayloadWithPriorityAndBusinessContext() {
        Map<String, Object> resolved = resolver.resolve(
                "OPERATION",
                "OPERATION_REPORT",
                77L,
                null,
                Map.of(
                        "businessContext", Map.of("selectedIdea", Map.of("title", "Cookie Brand")),
                        "operationInput", Map.of("period", "2026-06", "notes", "ad efficiency dropped"),
                        "operationReport", Map.of("selectedSuggestion", Map.of("title", "Improve ad conversion")),
                        "contextPriority", List.of("operationInput", "operationReport", "businessContext", "startupProfile")
                )
        );

        @SuppressWarnings("unchecked")
        Map<String, Object> businessContext = (Map<String, Object>) resolved.get("businessContext");
        @SuppressWarnings("unchecked")
        Map<String, Object> operationContext = (Map<String, Object>) resolved.get("operationContext");

        assertThat(businessContext)
                .containsEntry("selectedIdea", Map.of("title", "Cookie Brand"));
        assertThat(operationContext)
                .containsEntry("input", Map.of("period", "2026-06", "notes", "ad efficiency dropped"))
                .containsEntry("report", Map.of("selectedSuggestion", Map.of("title", "Improve ad conversion")));
        assertThat(resolved.get("contextPriority"))
                .isEqualTo(List.of("operationInput", "operationReport", "businessContext", "startupProfile"));
    }

    @Test
    void resolvesSnsFeaturePayloadWithCampaignContext() {
        Map<String, Object> resolved = resolver.resolve(
                "SNS",
                "SNS_REPORT",
                null,
                null,
                Map.of(
                        "campaignContext", Map.of(
                                "selectedIdea", Map.of("title", "Cookie Brand"),
                                "operationFocus", Map.of("title", "Improve ad conversion")
                        ),
                        "campaignDraft", Map.of(
                                "topic", "cookie promotion",
                                "channel", "INSTAGRAM_REELS",
                                "objective", "CONVERSION"
                        ),
                        "contextPriority", List.of("campaignDraft", "campaignContext", "startupProfile")
                )
        );

        @SuppressWarnings("unchecked")
        Map<String, Object> campaignContext = (Map<String, Object>) resolved.get("campaignContext");
        @SuppressWarnings("unchecked")
        Map<String, Object> campaignDraft = (Map<String, Object>) resolved.get("campaignDraft");

        assertThat(campaignContext)
                .containsEntry("selectedIdea", Map.of("title", "Cookie Brand"));
        assertThat(campaignDraft)
                .containsEntry("channel", "INSTAGRAM_REELS")
                .containsEntry("objective", "CONVERSION");
        assertThat(resolved.get("contextPriority"))
                .isEqualTo(List.of("campaignDraft", "campaignContext", "startupProfile"));
    }

    @Test
    void resolvesPlanFeaturePayloadWhenNullableFieldsAreExplicitlyNull() {
        Map<String, Object> currentResult = new LinkedHashMap<>();
        currentResult.put("planGoal", "ALIGN_SUPPORT");
        currentResult.put("focusedSection", null);
        currentResult.put("selectedSupportProgram", null);

        Map<String, Object> resolved = resolver.resolve(
                "PLAN",
                "PLAN_REPORT",
                null,
                null,
                currentResult
        );

        @SuppressWarnings("unchecked")
        Map<String, Object> planContext = (Map<String, Object>) resolved.get("planContext");
        @SuppressWarnings("unchecked")
        Map<String, Object> selection = (Map<String, Object>) resolved.get("selection");

        assertThat(planContext)
                .containsEntry("planGoal", "ALIGN_SUPPORT")
                .containsEntry("focusedSection", Map.of());
        assertThat(selection)
                .containsEntry("selectedSupportProgram", Map.of());
    }
}
