package com.kakao.backend.commercialarea.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(
        name = "commercial_area_metrics",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_area_industry_metric",
                columnNames = {"sido", "sigungu", "dong", "industry_large", "industry_medium", "industry_small"}
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class CommercialAreaMetric {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sido")
    private String sido;

    @Column(name = "sigungu")
    private String sigungu;

    @Column(name = "dong")
    private String dong;

    @Column(name = "industry_large")
    private String industryLarge;

    @Column(name = "industry_medium")
    private String industryMedium;

    @Column(name = "industry_small")
    private String industrySmall;

    @Column(name = "store_count")
    private Integer storeCount;

    @Column(name = "competitor_count")
    private Integer competitorCount;

    @Column(name = "calculated_at")
    private LocalDateTime calculatedAt = LocalDateTime.now();

    public static CommercialAreaMetric create() {
        return new CommercialAreaMetric();
    }
}
