package com.kakao.backend.commercialarea.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.kakao.backend.commercialarea.domain.CommercialRentReference;
import com.kakao.backend.commercialarea.dto.RentEstimateResponse;
import com.kakao.backend.commercialarea.repository.CommercialRentReferenceRepository;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CommercialRentReferenceServiceTest {

    @Mock
    private CommercialRentReferenceRepository rentReferenceRepository;

    @Test
    void fallsBackToDefaultCommercialTypeWhenSpecificTypeHasNoReferenceData() {
        CommercialRentReference reference = reference("서울", "마포구", "연남동", "소규모상가", "52.5");
        CommercialRentReferenceService service = new CommercialRentReferenceService(rentReferenceRepository);

        when(rentReferenceRepository.findTopByCommercialTypeOrderByBaseYearDescBaseQuarterDesc("카페"))
                .thenReturn(Optional.empty());
        when(rentReferenceRepository.findTopByCommercialTypeOrderByBaseYearDescBaseQuarterDesc("소규모상가"))
                .thenReturn(Optional.of(reference));
        when(rentReferenceRepository.findByCommercialTypeAndBaseYearAndBaseQuarter("소규모상가", 2026, 1))
                .thenReturn(List.of(reference));

        RentEstimateResponse response = service.estimate("서울", "마포구", "연남동", null, 33.0, "카페");

        assertThat(response.commercialType()).isEqualTo("소규모상가");
        assertThat(response.estimatedMonthlyRent()).isEqualTo(1_732_500);
        assertThat(response.matchLevel()).isEqualTo("AREA_AVERAGE");
    }

    private CommercialRentReference reference(
            String sido,
            String regionDepth2,
            String regionDepth3,
            String commercialType,
            String rentPerM2Thousand
    ) {
        CommercialRentReference reference = CommercialRentReference.create();
        reference.setSido(sido);
        reference.setRegionDepth2(regionDepth2);
        reference.setRegionDepth3(regionDepth3);
        reference.setCommercialType(commercialType);
        reference.setBaseYear(2026);
        reference.setBaseQuarter(1);
        reference.setRentPerM2Thousand(new BigDecimal(rentPerM2Thousand));
        reference.setSource("test");
        return reference;
    }
}
