package com.kakao.backend.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "business_idea_option")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class BusinessIdeaOption {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "idea_result_id", nullable = false)
    private BusinessIdeaResult ideaResult;

    @Column(name = "name", nullable = false)
    private String name;

    @Lob
    @Column(name = "description", columnDefinition = "text")
    private String description;

    @Column(name = "fit_score")
    private Integer fitScore;

    @Column(name = "difficulty_level")
    private String difficultyLevel;

    @Column(name = "profitability_level")
    private String profitabilityLevel;

    @Column(name = "target_customer")
    private String targetCustomer;

    @Column(name = "estimated_initial_cost")
    private Integer estimatedInitialCost;

    @Lob
    @Column(name = "reason", columnDefinition = "text")
    private String reason;

    @Column(name = "selected", nullable = false)
    private Boolean selected = false;
}
