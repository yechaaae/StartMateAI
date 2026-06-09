package com.kakao.backend.policy.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
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
import java.math.BigDecimal;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "support_program_rules")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SupportProgramRule extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "program_id")
    private SupportProgram program;

    @Column(name = "age_min")
    private Integer ageMin;

    @Column(name = "age_max")
    private Integer ageMax;

    @Lob
    @Column(name = "allowed_sidos", columnDefinition = "text")
    private String allowedSidos;

    @Lob
    @Column(name = "allowed_sigungu", columnDefinition = "text")
    private String allowedSigungu;

    @Lob
    @Column(name = "allowed_founder_types", columnDefinition = "text")
    private String allowedFounderTypes;

    @Lob
    @Column(name = "allowed_business_stages", columnDefinition = "text")
    private String allowedBusinessStages;

    @Column(name = "business_age_min_months")
    private Integer businessAgeMinMonths;

    @Column(name = "business_age_max_months")
    private Integer businessAgeMaxMonths;

    @Lob
    @Column(name = "allowed_industries", columnDefinition = "text")
    private String allowedIndustries;

    @Lob
    @Column(name = "excluded_industries", columnDefinition = "text")
    private String excludedIndustries;

    @Column(name = "requires_business_registration")
    private Boolean requiresBusinessRegistration;

    @Column(name = "allows_pre_founder")
    private Boolean allowsPreFounder;

    @Column(name = "rule_confidence")
    private BigDecimal ruleConfidence = BigDecimal.valueOf(0.5);

    @Column(name = "rule_source")
    private String ruleSource;
}
