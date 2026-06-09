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
import java.time.LocalDate;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "support_program_recommendation")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SupportProgramRecommendation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "support_program_match_id", nullable = false)
    private SupportProgramMatch supportProgramMatch;

    @Column(name = "program_name", nullable = false)
    private String programName;

    @Column(name = "organization_name")
    private String organizationName;

    @Column(name = "region")
    private String region;

    @Column(name = "start_date")
    private LocalDate startDate;

    @Column(name = "end_date")
    private LocalDate endDate;

    @Column(name = "match_score")
    private Integer matchScore;

    @Lob
    @Column(name = "eligibility_summary", columnDefinition = "text")
    private String eligibilitySummary;

    @Lob
    @Column(name = "document_checklist", columnDefinition = "text")
    private String documentChecklist;

    @Lob
    @Column(name = "caution", columnDefinition = "text")
    private String caution;

    @Column(name = "source_url")
    private String sourceUrl;
}
