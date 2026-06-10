package com.kakao.backend.commercialarea.service;

import com.kakao.backend.commercialarea.repository.CommercialRentReferenceRepository;
import java.nio.file.Files;
import java.nio.file.Path;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class CommercialRentReferenceDataLoader implements ApplicationRunner {

    private static final Path RENT_CSV_PATH = Path.of("data", "rent_small_commercial.csv");

    private final CommercialRentReferenceRepository rentReferenceRepository;
    private final CommercialRentReferenceService rentReferenceService;

    public CommercialRentReferenceDataLoader(
            CommercialRentReferenceRepository rentReferenceRepository,
            CommercialRentReferenceService rentReferenceService
    ) {
        this.rentReferenceRepository = rentReferenceRepository;
        this.rentReferenceService = rentReferenceService;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (rentReferenceRepository.count() > 0 || !Files.exists(RENT_CSV_PATH)) {
            return;
        }
        rentReferenceService.importCsv(
                RENT_CSV_PATH.toString(),
                "소규모상가",
                "부동산통계정보 임대동향 지역별 임대료"
        );
    }
}
