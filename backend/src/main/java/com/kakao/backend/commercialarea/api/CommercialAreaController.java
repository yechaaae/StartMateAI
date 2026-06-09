package com.kakao.backend.commercialarea.api;

import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import com.kakao.backend.commercialarea.dto.StoreImportRequest;
import com.kakao.backend.commercialarea.dto.StoreImportResponse;
import com.kakao.backend.commercialarea.service.CommercialAreaService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class CommercialAreaController {

    private final CommercialAreaService commercialAreaService;

    public CommercialAreaController(CommercialAreaService commercialAreaService) {
        this.commercialAreaService = commercialAreaService;
    }

    @PostMapping("/stores/import-csv")
    public StoreImportResponse importCsv(@RequestBody StoreImportRequest request) {
        return commercialAreaService.importCsv(request.filePath(), request.region());
    }

    @PostMapping("/commercial-areas/analyze")
    public CommercialAreaResponse analyze(@RequestBody CommercialAreaRequest request) {
        return commercialAreaService.analyze(request);
    }
}
