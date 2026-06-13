package com.kakao.backend.operation.application;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.operation.domain.OperationFeedback;
import com.kakao.backend.operation.domain.OperationMetric;
import com.kakao.backend.operation.dto.OperationFeedbackRequest;
import com.kakao.backend.operation.dto.OperationFeedbackResponse;
import com.kakao.backend.operation.infrastructure.OperationFeedbackRepository;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.SavedResult;
import com.kakao.backend.workspace.domain.Workspace;
import com.kakao.backend.workspace.infrastructure.SavedResultRepository;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.YearMonth;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OperationFeedbackService {

    private static final BigDecimal ONE_HUNDRED = new BigDecimal("100.0");

    private final OperationFeedbackRepository operationFeedbackRepository;
    private final SavedResultRepository savedResultRepository;
    private final WorkspaceRepository workspaceRepository;
    private final UserRepository userRepository;
    private final ObjectMapper objectMapper;

    public OperationFeedbackService(
            OperationFeedbackRepository operationFeedbackRepository,
            SavedResultRepository savedResultRepository,
            WorkspaceRepository workspaceRepository,
            UserRepository userRepository,
            ObjectMapper objectMapper
    ) {
        this.operationFeedbackRepository = operationFeedbackRepository;
        this.savedResultRepository = savedResultRepository;
        this.workspaceRepository = workspaceRepository;
        this.userRepository = userRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public OperationFeedbackResponse save(Long userId, OperationFeedbackRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));
        validateProductShares(request.products());

        Workspace workspace = workspaceRepository.findFirstByUserIdAndStatusOrderByIdAsc(userId, "ACTIVE")
                .orElseGet(() -> {
                    Workspace created = Workspace.create("Operation feedback workspace", "ACTIVE");
                    created.setUser(user);
                    return workspaceRepository.save(created);
                });

        OperationFeedback feedback = OperationFeedback.create();
        feedback.setWorkspace(workspace);
        applyPeriod(feedback, request.period());
        applyKpis(feedback, request.kpis());
        feedback.setFeedbackSummary(summaryFrom(request));
        feedback.setNextActionPlan(actionPlanFrom(request));
        addMetrics(feedback, request);

        OperationFeedback savedFeedback = operationFeedbackRepository.save(feedback);
        SavedResult savedResult = savedResultRepository.save(SavedResult.create(
                workspace,
                "operation",
                "OPERATION_REPORT",
                savedFeedback.getId(),
                titleFrom(request),
                summaryFrom(request),
                payloadFrom(request, savedFeedback.getId())
        ));

        return new OperationFeedbackResponse(
                savedFeedback.getId(),
                workspace.getId(),
                savedResult.getId(),
                true
        );
    }

    private void applyPeriod(OperationFeedback feedback, String period) {
        if (period == null || period.isBlank()) {
            return;
        }

        YearMonth yearMonth = YearMonth.parse(period.trim());
        LocalDate start = yearMonth.atDay(1);
        feedback.setPeriodStart(start);
        feedback.setPeriodEnd(yearMonth.atEndOfMonth());
    }

    private void applyKpis(OperationFeedback feedback, List<OperationFeedbackRequest.KpiRequest> kpis) {
        for (OperationFeedbackRequest.KpiRequest kpi : safeList(kpis)) {
            if ("totalSales".equals(kpi.key())) {
                feedback.setTotalSales(integerValue(kpi.current()));
            } else if ("totalCost".equals(kpi.key())) {
                feedback.setTotalCost(integerValue(kpi.current()));
            } else if ("orderCount".equals(kpi.key())) {
                feedback.setOrderCount(integerValue(kpi.current()));
            } else if ("adConversionRate".equals(kpi.key())) {
                feedback.setAdConversionRate(oneDecimal(kpi.current()));
            }
        }
    }

    private void addMetrics(OperationFeedback feedback, OperationFeedbackRequest request) {
        for (OperationFeedbackRequest.KpiRequest kpi : safeList(request.kpis())) {
            addMetric(feedback, "KPI", text(kpi.label(), kpi.key()), kpi.current(), kpi.unit(), "previous=" + valueText(kpi.previous()));
        }
        for (OperationFeedbackRequest.ProductShareRequest product : safeList(request.products())) {
            addMetric(
                    feedback,
                    "PRODUCT_SHARE",
                    product.name(),
                    oneDecimal(product.share()),
                    "%",
                    product.isLocked() ? "상품 매출 비중 (고정)" : "상품 매출 비중"
            );
        }
        for (List<String> channel : safeList(request.channels())) {
            if (channel == null || channel.isEmpty()) {
                continue;
            }
            addMetric(feedback, "CHANNEL_NOTE", channel.get(0), BigDecimal.ZERO, "", channel.size() > 1 ? channel.get(1) : "");
        }
        if (request.selectedSuggestionTitle() != null && !request.selectedSuggestionTitle().isBlank()) {
            addMetric(feedback, "SELECTED_SUGGESTION", request.selectedSuggestionTitle(), BigDecimal.ZERO, "", "선택된 개선 제안");
        }
    }

    private void addMetric(
            OperationFeedback feedback,
            String type,
            String name,
            BigDecimal value,
            String unit,
            String description
    ) {
        feedback.getMetrics().add(OperationMetric.create(
                feedback,
                type,
                name,
                value == null ? BigDecimal.ZERO : value,
                unit,
                description
        ));
    }

    private void validateProductShares(List<OperationFeedbackRequest.ProductShareRequest> products) {
        List<OperationFeedbackRequest.ProductShareRequest> list = safeList(products);
        if (list.isEmpty()) {
            // 상품을 등록하지 않은 경우 KPI만 저장할 수 있도록 비중 검증을 건너뛴다.
            return;
        }

        for (OperationFeedbackRequest.ProductShareRequest product : list) {
            BigDecimal share = product.share() == null ? BigDecimal.ZERO : product.share();
            if (share.compareTo(BigDecimal.ZERO) < 0 || share.compareTo(ONE_HUNDRED) > 0) {
                throw new IllegalArgumentException("Product shares must be between 0 and 100.");
            }
        }

        BigDecimal total = list.stream()
                .map(OperationFeedbackRequest.ProductShareRequest::share)
                .map(value -> (value == null ? BigDecimal.ZERO : value).setScale(1, RoundingMode.HALF_UP))
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .setScale(1, RoundingMode.HALF_UP);

        if (total.compareTo(ONE_HUNDRED) != 0) {
            throw new IllegalArgumentException("Product shares must total 100.");
        }
    }

    private String payloadFrom(OperationFeedbackRequest request, Long feedbackId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        Map<String, Object> reportData = new LinkedHashMap<>();
        reportData.put("period", request.period());
        reportData.put("kpis", safeList(request.kpis()));
        reportData.put("products", safeList(request.products()));
        reportData.put("channels", safeList(request.channels()));
        reportData.put("notes", request.notes() == null ? "" : request.notes());
        reportData.put("suggestions", safeList(request.suggestions()));
        payload.put("featureId", "operation");
        payload.put("operationFeedbackId", feedbackId);
        payload.put("reportData", reportData);

        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Operation feedback payload could not be serialized.", exception);
        }
    }

    private String titleFrom(OperationFeedbackRequest request) {
        return text(request.period(), "운영") + " 운영 피드백 리포트";
    }

    private String summaryFrom(OperationFeedbackRequest request) {
        if (request.selectedSuggestionTitle() != null && !request.selectedSuggestionTitle().isBlank()) {
            return request.selectedSuggestionTitle() + " 제안을 포함한 운영 피드백입니다.";
        }
        return "운영 입력값 기반 MOCK 피드백입니다.";
    }

    private String actionPlanFrom(OperationFeedbackRequest request) {
        return safeList(request.suggestions()).stream()
                .findFirst()
                .map(OperationFeedbackRequest.SuggestionRequest::body)
                .orElse("다음 입력 때 같은 기준으로 지표를 비교합니다.");
    }

    private int integerValue(BigDecimal value) {
        return value == null ? 0 : value.setScale(0, RoundingMode.HALF_UP).intValue();
    }

    private BigDecimal oneDecimal(BigDecimal value) {
        return (value == null ? BigDecimal.ZERO : value)
                .max(BigDecimal.ZERO)
                .min(ONE_HUNDRED)
                .setScale(1, RoundingMode.HALF_UP);
    }

    private String valueText(BigDecimal value) {
        return value == null ? "0" : value.stripTrailingZeros().toPlainString();
    }

    private String text(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private <T> List<T> safeList(List<T> values) {
        return values == null ? List.of() : values;
    }
}
