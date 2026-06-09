package com.kakao.backend.policy.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDate;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(
        name = "support_programs",
        uniqueConstraints = @UniqueConstraint(name = "uk_support_program_source_id", columnNames = {"source", "source_id"})
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SupportProgram extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "source", nullable = false)
    private String source;

    @Column(name = "source_id")
    private String sourceId;

    @Column(name = "source_url")
    private String sourceUrl;

    @Column(name = "title", nullable = false)
    private String title;

    @Lob
    @Column(name = "summary", columnDefinition = "text")
    private String summary;

    @Lob
    @Column(name = "content", columnDefinition = "text")
    private String content;

    @Column(name = "category")
    private String category;

    @Column(name = "support_type")
    private String supportType;

    @Lob
    @Column(name = "target", columnDefinition = "text")
    private String target;

    @Column(name = "age_condition")
    private String ageCondition;

    @Column(name = "business_stage_condition")
    private String businessStageCondition;

    @Column(name = "region_condition")
    private String regionCondition;

    @Column(name = "industry_condition")
    private String industryCondition;

    @Column(name = "organization")
    private String organization;

    @Column(name = "department")
    private String department;

    @Column(name = "contact")
    private String contact;

    @Column(name = "application_start_date")
    private LocalDate applicationStartDate;

    @Column(name = "application_end_date")
    private LocalDate applicationEndDate;

    @Column(name = "status")
    private String status;

    @Column(name = "support_amount")
    private String supportAmount;

    @Lob
    @Column(name = "required_documents", columnDefinition = "text")
    private String requiredDocuments;

    @Column(name = "apply_url")
    private String applyUrl;

    @Column(name = "detail_url")
    private String detailUrl;

    @Lob
    @Column(name = "tags", columnDefinition = "text")
    private String tags;

    @Lob
    @Column(name = "raw_payload", columnDefinition = "longtext")
    private String rawPayload;

    public static SupportProgram create() {
        return new SupportProgram();
    }
}
