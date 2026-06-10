package com.kakao.backend.aichat.application;

import com.kakao.backend.idea.domain.BusinessIdeaOption;
import com.kakao.backend.idea.domain.BusinessIdeaResult;
import com.kakao.backend.idea.infrastructure.BusinessIdeaResultRepository;
import com.kakao.backend.operation.domain.OperationFeedback;
import com.kakao.backend.operation.domain.OperationMetric;
import com.kakao.backend.operation.infrastructure.OperationFeedbackRepository;
import com.kakao.backend.policy.domain.SupportProgramMatch;
import com.kakao.backend.policy.domain.SupportProgramRecommendation;
import com.kakao.backend.policy.infrastructure.SupportProgramMatchRepository;
import com.kakao.backend.simulation.domain.SimulationDetail;
import com.kakao.backend.simulation.domain.SimulationResult;
import com.kakao.backend.simulation.infrastructure.SimulationResultRepository;
import com.kakao.backend.workspace.domain.SavedResult;
import com.kakao.backend.workspace.infrastructure.SavedResultRepository;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AiChatReferenceContextService {

    private final BusinessIdeaResultRepository businessIdeaResultRepository;
    private final SupportProgramMatchRepository supportProgramMatchRepository;
    private final OperationFeedbackRepository operationFeedbackRepository;
    private final SimulationResultRepository simulationResultRepository;
    private final SavedResultRepository savedResultRepository;

    public AiChatReferenceContextService(
            BusinessIdeaResultRepository businessIdeaResultRepository,
            SupportProgramMatchRepository supportProgramMatchRepository,
            OperationFeedbackRepository operationFeedbackRepository,
            SimulationResultRepository simulationResultRepository,
            SavedResultRepository savedResultRepository
    ) {
        this.businessIdeaResultRepository = businessIdeaResultRepository;
        this.supportProgramMatchRepository = supportProgramMatchRepository;
        this.operationFeedbackRepository = operationFeedbackRepository;
        this.simulationResultRepository = simulationResultRepository;
        this.savedResultRepository = savedResultRepository;
    }

    public Map<String, Object> resolve(AiChatDispatchCommand command) {
        if (command == null || command.currentResultId() == null || isBlank(command.currentResultType())) {
            return Map.of();
        }

        String type = normalize(command.currentResultType());
        Long workspaceId = command.workspace() != null ? command.workspace().getId() : null;

        return switch (type) {
            case "BUSINESS_IDEA_RESULT", "IDEA_REPORT" -> businessIdeaResultRepository.findById(command.currentResultId())
                    .filter(result -> ownsWorkspace(workspaceId, result.getWorkspace() != null ? result.getWorkspace().getId() : null))
                    .map(this::toIdeaReference)
                    .orElse(Map.of());
            case "SUPPORT_PROGRAM_MATCH", "SUPPORT_REPORT", "POLICY_REPORT" -> supportProgramMatchRepository.findById(command.currentResultId())
                    .filter(result -> ownsWorkspace(workspaceId, result.getWorkspace() != null ? result.getWorkspace().getId() : null))
                    .map(this::toSupportReference)
                    .orElse(Map.of());
            case "OPERATION_FEEDBACK", "OPERATION_REPORT" -> operationFeedbackRepository.findById(command.currentResultId())
                    .filter(result -> ownsWorkspace(workspaceId, result.getWorkspace() != null ? result.getWorkspace().getId() : null))
                    .map(this::toOperationReference)
                    .orElse(Map.of());
            case "SIMULATION_RESULT", "SIMULATION_REPORT" -> simulationResultRepository.findById(command.currentResultId())
                    .filter(result -> ownsWorkspace(workspaceId, result.getWorkspace() != null ? result.getWorkspace().getId() : null))
                    .map(this::toSimulationReference)
                    .orElse(Map.of());
            case "SAVED_RESULT" -> savedResultRepository.findById(command.currentResultId())
                    .filter(result -> ownsWorkspace(workspaceId, result.getWorkspace() != null ? result.getWorkspace().getId() : null))
                    .map(this::toSavedReference)
                    .orElse(Map.of());
            default -> Map.of();
        };
    }

    private boolean ownsWorkspace(Long expectedWorkspaceId, Long actualWorkspaceId) {
        if (expectedWorkspaceId == null || actualWorkspaceId == null) {
            return true;
        }
        return expectedWorkspaceId.equals(actualWorkspaceId);
    }

    private Map<String, Object> toIdeaReference(BusinessIdeaResult result) {
        List<Map<String, Object>> options = result.getOptions().stream()
                .map(this::toIdeaOption)
                .toList();

        return reference(
                "BUSINESS_IDEA_RESULT",
                result.getId(),
                result.getTitle(),
                result.getSummary(),
                dataMap()
                        .with("chatRoomId", result.getChatRoomId())
                        .with("inputSnapshot", result.getInputSnapshot())
                        .with("options", options)
                        .build()
        );
    }

    private Map<String, Object> toSupportReference(SupportProgramMatch match) {
        List<Map<String, Object>> recommendations = match.getRecommendations().stream()
                .map(this::toSupportRecommendation)
                .toList();

        return reference(
                "SUPPORT_PROGRAM_MATCH",
                match.getId(),
                "지원사업 추천 결과",
                match.getSearchConditionSnapshot(),
                dataMap()
                        .with("chatRoomId", match.getChatRoomId())
                        .with("recommendations", recommendations)
                        .build()
        );
    }

    private Map<String, Object> toOperationReference(OperationFeedback feedback) {
        List<Map<String, Object>> metrics = feedback.getMetrics().stream()
                .map(this::toOperationMetric)
                .toList();

        return reference(
                "OPERATION_FEEDBACK",
                feedback.getId(),
                "운영 피드백 결과",
                feedback.getFeedbackSummary(),
                dataMap()
                        .with("chatRoomId", feedback.getChatRoomId())
                        .with("periodStart", stringValue(feedback.getPeriodStart()))
                        .with("periodEnd", stringValue(feedback.getPeriodEnd()))
                        .with("totalSales", feedback.getTotalSales())
                        .with("totalCost", feedback.getTotalCost())
                        .with("orderCount", feedback.getOrderCount())
                        .with("adConversionRate", feedback.getAdConversionRate())
                        .with("nextActionPlan", feedback.getNextActionPlan())
                        .with("metrics", metrics)
                        .build()
        );
    }

    private Map<String, Object> toSimulationReference(SimulationResult result) {
        List<Map<String, Object>> details = result.getDetails().stream()
                .map(this::toSimulationDetail)
                .toList();

        return reference(
                "SIMULATION_RESULT",
                result.getId(),
                "시뮬레이션 결과",
                result.getRiskSummary(),
                dataMap()
                        .with("chatRoomId", result.getChatRoomId())
                        .with("simulationType", result.getSimulationType())
                        .with("initialBudget", result.getInitialBudget())
                        .with("expectedRevenue", result.getExpectedRevenue())
                        .with("expectedCost", result.getExpectedCost())
                        .with("expectedProfit", result.getExpectedProfit())
                        .with("breakEvenPoint", result.getBreakEvenPoint())
                        .with("recommendation", result.getRecommendation())
                        .with("details", details)
                        .build()
        );
    }

    private Map<String, Object> toSavedReference(SavedResult savedResult) {
        return reference(
                savedResult.getResultType(),
                savedResult.getReferenceId(),
                savedResult.getTitle(),
                savedResult.getSummary(),
                dataMap().with("savedResultId", savedResult.getId()).build()
        );
    }

    private Map<String, Object> toIdeaOption(BusinessIdeaOption option) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", option.getId());
        item.put("name", option.getName());
        item.put("description", option.getDescription());
        item.put("fitScore", option.getFitScore());
        item.put("difficultyLevel", option.getDifficultyLevel());
        item.put("profitabilityLevel", option.getProfitabilityLevel());
        item.put("targetCustomer", option.getTargetCustomer());
        item.put("estimatedInitialCost", option.getEstimatedInitialCost());
        item.put("reason", option.getReason());
        item.put("selected", option.getSelected());
        return item;
    }

    private Map<String, Object> toSupportRecommendation(SupportProgramRecommendation recommendation) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", recommendation.getId());
        item.put("programName", recommendation.getProgramName());
        item.put("organizationName", recommendation.getOrganizationName());
        item.put("region", recommendation.getRegion());
        item.put("startDate", stringValue(recommendation.getStartDate()));
        item.put("endDate", stringValue(recommendation.getEndDate()));
        item.put("matchScore", recommendation.getMatchScore());
        item.put("eligibilitySummary", recommendation.getEligibilitySummary());
        item.put("documentChecklist", recommendation.getDocumentChecklist());
        item.put("caution", recommendation.getCaution());
        item.put("sourceUrl", recommendation.getSourceUrl());
        return item;
    }

    private Map<String, Object> toOperationMetric(OperationMetric metric) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", metric.getId());
        item.put("metricType", metric.getMetricType());
        item.put("metricName", metric.getMetricName());
        item.put("metricValue", metric.getMetricValue());
        item.put("unit", metric.getUnit());
        item.put("description", metric.getDescription());
        return item;
    }

    private Map<String, Object> toSimulationDetail(SimulationDetail detail) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", detail.getId());
        item.put("day", detail.getDay());
        item.put("title", detail.getTitle());
        item.put("actionItem", detail.getActionItem());
        item.put("riskMessage", detail.getRiskMessage());
        item.put("recommendation", detail.getRecommendation());
        return item;
    }

    private Map<String, Object> reference(
            String referenceType,
            Long referenceId,
            String title,
            String summary,
            Map<String, Object> data
    ) {
        Map<String, Object> reference = new LinkedHashMap<>();
        reference.put("referenceType", referenceType);
        reference.put("referenceId", referenceId);
        reference.put("title", title);
        reference.put("summary", summary);
        reference.put("data", data);
        return reference;
    }

    private DataMapBuilder dataMap() {
        return new DataMapBuilder();
    }

    private String normalize(String type) {
        return type == null ? "" : type.trim().toUpperCase();
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private String stringValue(Object value) {
        return Optional.ofNullable(value).map(Object::toString).orElse(null);
    }

    private static final class DataMapBuilder {

        private final Map<String, Object> values = new LinkedHashMap<>();

        private DataMapBuilder with(String key, Object value) {
            if (value != null) {
                values.put(key, value);
            }
            return this;
        }

        private Map<String, Object> build() {
            return values;
        }
    }
}
