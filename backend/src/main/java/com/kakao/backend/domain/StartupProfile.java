package com.kakao.backend.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "startup_profile")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class StartupProfile extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false, unique = true)
    private User user;

    @Column(name = "major")
    private String major;

    @Column(name = "career")
    private String career;

    @Column(name = "interest_field")
    private String interestField;

    @Column(name = "residence_region")
    private String residenceRegion;

    @Column(name = "business_region")
    private String businessRegion;

    @Column(name = "initial_budget")
    private Integer initialBudget;

    @Column(name = "team_status")
    private String teamStatus;

    @Column(name = "preferred_business_type")
    private String preferredBusinessType;

    @Lob
    @Column(name = "strength_tags", columnDefinition = "text")
    private String strengthTags;

    @Column(name = "suitability_score")
    private Integer suitabilityScore;

    @Lob
    @Column(name = "diagnosis_summary", columnDefinition = "text")
    private String diagnosisSummary;
}
