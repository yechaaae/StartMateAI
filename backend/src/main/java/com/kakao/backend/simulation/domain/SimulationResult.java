package com.kakao.backend.simulation.domain;

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
import java.util.ArrayList;
import java.util.List;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "simulation_result")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SimulationResult extends BaseTimeEntity {

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

    @Column(name = "simulation_type")
    private String simulationType;

    @Column(name = "initial_budget")
    private Integer initialBudget;

    @Column(name = "expected_revenue")
    private Integer expectedRevenue;

    @Column(name = "expected_cost")
    private Integer expectedCost;

    @Column(name = "expected_profit")
    private Integer expectedProfit;

    @Column(name = "break_even_point")
    private Integer breakEvenPoint;

    @Lob
    @Column(name = "risk_summary", columnDefinition = "text")
    private String riskSummary;

    @Lob
    @Column(name = "recommendation", columnDefinition = "text")
    private String recommendation;

    @OneToMany(mappedBy = "simulationResult", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<SimulationDetail> details = new ArrayList<>();
}
