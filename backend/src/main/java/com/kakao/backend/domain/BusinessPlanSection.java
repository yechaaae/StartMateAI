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
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "business_plan_section")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class BusinessPlanSection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "business_plan_id", nullable = false)
    private BusinessPlan businessPlan;

    @Column(name = "section_type", nullable = false)
    private String sectionType;

    @Column(name = "section_title", nullable = false)
    private String sectionTitle;

    @Lob
    @Column(name = "content", columnDefinition = "text")
    private String content;

    @Column(name = "sort_order")
    private Integer sortOrder;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    @PreUpdate
    private void updateTimestamp() {
        updatedAt = LocalDateTime.now();
    }
}
