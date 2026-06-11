package com.kakao.backend.commercialarea.api;

import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import com.kakao.backend.commercialarea.dto.RentEstimateResponse;
import com.kakao.backend.commercialarea.dto.RentReferenceImportRequest;
import com.kakao.backend.commercialarea.dto.RentReferenceImportResponse;
import com.kakao.backend.commercialarea.dto.StoreImportRequest;
import com.kakao.backend.commercialarea.dto.StoreImportResponse;
import com.kakao.backend.commercialarea.service.CommercialRentReferenceService;
import com.kakao.backend.commercialarea.service.CommercialAreaService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping
public class CommercialAreaController {

    private final CommercialAreaService commercialAreaService;
    private final CommercialRentReferenceService rentReferenceService;

    public CommercialAreaController(
            CommercialAreaService commercialAreaService,
            CommercialRentReferenceService rentReferenceService
    ) {
        this.commercialAreaService = commercialAreaService;
        this.rentReferenceService = rentReferenceService;
    }

    @PostMapping("/stores/import-csv")
    public StoreImportResponse importCsv(@RequestBody StoreImportRequest request) {
        return commercialAreaService.importCsv(request.filePath(), request.region());
    }

    @PostMapping("/commercial-areas/analyze")
    public CommercialAreaResponse analyze(@RequestBody CommercialAreaRequest request) {
        return commercialAreaService.analyze(request);
    }

    @PostMapping("/rent-references/import-csv")
    public RentReferenceImportResponse importRentCsv(@RequestBody RentReferenceImportRequest request) {
        return rentReferenceService.importCsv(request.filePath(), request.commercialType(), request.source());
    }

    @GetMapping("/rent-references/estimate")
    public RentEstimateResponse estimateRent(
            @RequestParam(required = false) String sido,
            @RequestParam(required = false) String sigungu,
            @RequestParam(required = false) String dong,
            @RequestParam(required = false) String address,
            @RequestParam(required = false) Double areaM2,
            @RequestParam(required = false) String commercialType
    ) {
        return rentReferenceService.estimate(sido, sigungu, dong, address, areaM2, commercialType);
    }
}
