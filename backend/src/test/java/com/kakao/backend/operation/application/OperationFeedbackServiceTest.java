package com.kakao.backend.operation.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.operation.domain.OperationFeedback;
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
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class OperationFeedbackServiceTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Mock
    private OperationFeedbackRepository operationFeedbackRepository;

    @Mock
    private SavedResultRepository savedResultRepository;

    @Mock
    private WorkspaceRepository workspaceRepository;

    @Mock
    private UserRepository userRepository;

    @Test
    void savesOperationFeedbackAndSavedResultForUserWorkspace() throws Exception {
        OperationFeedbackService service = service();
        User user = User.create("owner@example.com", "owner", "USER");
        user.setId(7L);
        Workspace workspace = Workspace.create("workspace", "ACTIVE");
        workspace.setId(11L);
        workspace.setUser(user);

        when(userRepository.findById(7L)).thenReturn(Optional.of(user));
        when(workspaceRepository.findFirstByUserIdAndStatusOrderByIdAsc(7L, "ACTIVE")).thenReturn(Optional.of(workspace));
        when(operationFeedbackRepository.save(any(OperationFeedback.class))).thenAnswer(invocation -> {
            OperationFeedback feedback = invocation.getArgument(0);
            feedback.setId(31L);
            return feedback;
        });
        when(savedResultRepository.save(any(SavedResult.class))).thenAnswer(invocation -> invocation.getArgument(0));

        OperationFeedbackResponse response = service.save(7L, requestWithProductShares(60, 40));

        assertThat(response.id()).isEqualTo(31L);
        assertThat(response.savedResultCreated()).isTrue();

        ArgumentCaptor<OperationFeedback> feedbackCaptor = ArgumentCaptor.forClass(OperationFeedback.class);
        verify(operationFeedbackRepository).save(feedbackCaptor.capture());
        OperationFeedback feedback = feedbackCaptor.getValue();
        assertThat(feedback.getWorkspace()).isEqualTo(workspace);
        assertThat(feedback.getTotalSales()).isEqualTo(3000000);
        assertThat(feedback.getTotalCost()).isEqualTo(1200000);
        assertThat(feedback.getOrderCount()).isEqualTo(500);
        assertThat(feedback.getAdConversionRate()).isEqualByComparingTo(new BigDecimal("2.5"));
        assertThat(feedback.getMetrics()).hasSize(8);

        ArgumentCaptor<SavedResult> savedResultCaptor = ArgumentCaptor.forClass(SavedResult.class);
        verify(savedResultRepository).save(savedResultCaptor.capture());
        SavedResult savedResult = savedResultCaptor.getValue();
        assertThat(savedResult.getWorkspace()).isEqualTo(workspace);
        assertThat(savedResult.getSourceFeature()).isEqualTo("operation");
        assertThat(savedResult.getResultType()).isEqualTo("OPERATION_REPORT");
        assertThat(savedResult.getReferenceId()).isEqualTo(31L);
        Map<String, Object> payload = objectMapper.readValue(savedResult.getPayload(), new TypeReference<>() {
        });
        assertThat(payload.get("featureId")).isEqualTo("operation");
        assertThat(payload.get("reportData")).isInstanceOf(Map.class);
    }

    @Test
    void rejectsProductSharesWhenTotalIsNotOneHundred() {
        OperationFeedbackService service = service();
        when(userRepository.findById(7L)).thenReturn(Optional.of(User.create("owner@example.com", "owner", "USER")));

        assertThatThrownBy(() -> service.save(7L, requestWithProductShares(70, 20)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Product shares must total 100");
    }

    private OperationFeedbackRequest requestWithProductShares(double firstShare, double secondShare) {
        return new OperationFeedbackRequest(
                "2026-06",
                List.of(
                        new OperationFeedbackRequest.KpiRequest("totalSales", "매출", "원", new BigDecimal("3000000"), new BigDecimal("2500000")),
                        new OperationFeedbackRequest.KpiRequest("totalCost", "지출", "원", new BigDecimal("1200000"), new BigDecimal("1100000")),
                        new OperationFeedbackRequest.KpiRequest("orderCount", "주문 수", "건", new BigDecimal("500"), new BigDecimal("450")),
                        new OperationFeedbackRequest.KpiRequest("adConversionRate", "광고 전환율", "%", new BigDecimal("2.5"), new BigDecimal("2.0"))
                ),
                List.of(
                        new OperationFeedbackRequest.ProductShareRequest("아메리카노", BigDecimal.valueOf(firstShare)),
                        new OperationFeedbackRequest.ProductShareRequest("쿠키", BigDecimal.valueOf(secondShare))
                ),
                List.of(List.of("인스타그램 광고", "전환율 2.5%")),
                "광고 효율 점검",
                List.of(new OperationFeedbackRequest.SuggestionRequest("광고 전환율 회복", "소재를 교체합니다.", "sns")),
                "광고 전환율 회복"
        );
    }

    private OperationFeedbackService service() {
        return new OperationFeedbackService(
                operationFeedbackRepository,
                savedResultRepository,
                workspaceRepository,
                userRepository,
                objectMapper
        );
    }
}
