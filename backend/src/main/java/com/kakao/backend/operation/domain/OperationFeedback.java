package com.kakao.backend.operation.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
import com.kakao.backend.idea.domain.BusinessIdeaOption;
import com.kakao.backend.workspace.domain.Workspace;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "operation_feedback")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class OperationFeedback extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "business_idea_option_id")
    private BusinessIdeaOption businessIdeaOption;

    @Column(name = "chat_room_id")
    private Long chatRoomId;

    @Column(name = "period_start")
    private LocalDate periodStart;

    @Column(name = "period_end")
    private LocalDate periodEnd;

    @Column(name = "total_sales")
    private Integer totalSales;

    @Column(name = "total_cost")
    private Integer totalCost;

    @Column(name = "order_count")
    private Integer orderCount;

    @Column(name = "ad_conversion_rate", precision = 10, scale = 4)
    private BigDecimal adConversionRate;

    @Lob
    @Column(name = "feedback_summary", columnDefinition = "text")
    private String feedbackSummary;

    @Lob
    @Column(name = "next_action_plan", columnDefinition = "text")
    private String nextActionPlan;

    @OneToMany(mappedBy = "operationFeedback", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OperationMetric> metrics = new ArrayList<>();

    public static OperationFeedback create() {
        return new OperationFeedback();
    }
}
