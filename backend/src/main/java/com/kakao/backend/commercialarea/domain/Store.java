package com.kakao.backend.commercialarea.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(
        name = "stores",
        uniqueConstraints = @UniqueConstraint(name = "uk_store_source_id", columnNames = {"source", "source_store_id"})
)
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Store extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "source", nullable = false)
    private String source;

    @Column(name = "source_store_id")
    private String sourceStoreId;

    @Column(name = "store_name")
    private String storeName;

    @Column(name = "category_large")
    private String categoryLarge;

    @Column(name = "category_medium")
    private String categoryMedium;

    @Column(name = "category_small")
    private String categorySmall;

    @Column(name = "industry_code")
    private String industryCode;

    @Column(name = "industry_name")
    private String industryName;

    @Column(name = "sido")
    private String sido;

    @Column(name = "sigungu")
    private String sigungu;

    @Column(name = "dong")
    private String dong;

    @Column(name = "road_address")
    private String roadAddress;

    @Column(name = "jibun_address")
    private String jibunAddress;

    @Column(name = "longitude")
    private Double longitude;

    @Column(name = "latitude")
    private Double latitude;

    @Lob
    @Column(name = "raw_payload", columnDefinition = "longtext")
    private String rawPayload;

    public static Store create() {
        return new Store();
    }
}
