package com.kakao.backend.commercialarea.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.math.BigDecimal;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(
        name = "commercial_rent_references",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_commercial_rent_reference",
                columnNames = {"commercial_type", "base_year", "base_quarter", "sido", "region_depth2", "region_depth3"}
        )
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class CommercialRentReference {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sido", nullable = false)
    private String sido;

    @Column(name = "region_depth2")
    private String regionDepth2;

    @Column(name = "region_depth3")
    private String regionDepth3;

    @Column(name = "commercial_type", nullable = false)
    private String commercialType;

    @Column(name = "base_year", nullable = false)
    private Integer baseYear;

    @Column(name = "base_quarter", nullable = false)
    private Integer baseQuarter;

    @Column(name = "rent_per_m2_thousand", precision = 10, scale = 2, nullable = false)
    private BigDecimal rentPerM2Thousand;

    @Column(name = "source")
    private String source;

    public static CommercialRentReference create() {
        return new CommercialRentReference();
    }
}
