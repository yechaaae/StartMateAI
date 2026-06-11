package com.kakao.backend.seed.api;

import com.kakao.backend.commercialarea.service.CommercialAreaService;
import com.kakao.backend.policy.service.SupportProgramService;
import com.kakao.backend.seed.dto.SeedImportResponse;
import com.kakao.backend.seed.service.SeedKnowledgeService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/seeds")
public class SeedController {

    private final SeedKnowledgeService seedKnowledgeService;
    private final SupportProgramService supportProgramService;
    private final CommercialAreaService commercialAreaService;

    public SeedController(
            SeedKnowledgeService seedKnowledgeService,
            SupportProgramService supportProgramService,
            CommercialAreaService commercialAreaService
    ) {
        this.seedKnowledgeService = seedKnowledgeService;
        this.supportProgramService = supportProgramService;
        this.commercialAreaService = commercialAreaService;
    }

    @PostMapping("/import")
    public SeedImportResponse importSeeds() {
        int seedItems = seedKnowledgeService.importDefaultItems();
        int supportPrograms = supportProgramService.upsertDemoPrograms();
        int stores = commercialAreaService.importCsv(null, null).imported();
        return new SeedImportResponse(seedItems, supportPrograms, stores);
    }
}
