package com.kakao.backend.commercialarea.repository;

import com.kakao.backend.commercialarea.domain.CommercialAreaMetric;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CommercialAreaMetricRepository extends JpaRepository<CommercialAreaMetric, Long> {

    Optional<CommercialAreaMetric> findFirstBySidoAndSigunguAndDongAndIndustryLargeAndIndustryMediumAndIndustrySmallOrderByIdAsc(
            String sido,
            String sigungu,
            String dong,
            String industryLarge,
            String industryMedium,
            String industrySmall
    );
}
