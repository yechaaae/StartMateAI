package com.kakao.backend.commercialarea.repository;

import com.kakao.backend.commercialarea.domain.CommercialRentReference;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CommercialRentReferenceRepository extends JpaRepository<CommercialRentReference, Long> {

    void deleteByCommercialType(String commercialType);

    Optional<CommercialRentReference> findTopByCommercialTypeOrderByBaseYearDescBaseQuarterDesc(String commercialType);

    List<CommercialRentReference> findByCommercialTypeAndBaseYearAndBaseQuarter(
            String commercialType,
            Integer baseYear,
            Integer baseQuarter
    );
}
