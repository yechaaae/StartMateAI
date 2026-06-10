package com.kakao.backend.internal;

import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import com.kakao.backend.commercialarea.service.CommercialAreaService;
import com.kakao.backend.policy.dto.RecommendedProgramResponse;
import com.kakao.backend.policy.dto.SupportProgramRecommendationRequest;
import com.kakao.backend.policy.dto.SupportProgramSyncResponse;
import com.kakao.backend.policy.service.SupportProgramService;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/internal/ai-tools")
public class InternalAiToolController {

    private static final String INTERNAL_TOKEN_HEADER = "X-Startmate-Internal-Token";

    private final InternalToolAuthService internalToolAuthService;
    private final SupportProgramService supportProgramService;
    private final CommercialAreaService commercialAreaService;

    public InternalAiToolController(
            InternalToolAuthService internalToolAuthService,
            SupportProgramService supportProgramService,
            CommercialAreaService commercialAreaService
    ) {
        this.internalToolAuthService = internalToolAuthService;
        this.supportProgramService = supportProgramService;
        this.commercialAreaService = commercialAreaService;
    }

    @PostMapping("/support-programs/sync")
    public SupportProgramSyncResponse syncSupportPrograms(
            @RequestHeader(value = INTERNAL_TOKEN_HEADER, required = false) String token,
            @RequestParam(defaultValue = "all") String source
    ) {
        internalToolAuthService.verify(token);
        return supportProgramService.sync(source);
    }

    @PostMapping("/support-programs/recommend")
    public List<RecommendedProgramResponse> recommendSupportPrograms(
            @RequestHeader(value = INTERNAL_TOKEN_HEADER, required = false) String token,
            @RequestBody SupportProgramRecommendationRequest request
    ) {
        internalToolAuthService.verify(token);
        return supportProgramService.recommendWithDemoFallback(request);
    }

    @GetMapping("/support-programs")
    public List<Map<String, Object>> exportSupportPrograms(
            @RequestHeader(value = INTERNAL_TOKEN_HEADER, required = false) String token
    ) {
        internalToolAuthService.verify(token);
        return supportProgramService.exportForAiIndex();
    }

    @PostMapping("/commercial-areas/analyze")
    public CommercialAreaResponse analyzeCommercialArea(
            @RequestHeader(value = INTERNAL_TOKEN_HEADER, required = false) String token,
            @RequestBody CommercialAreaRequest request
    ) {
        internalToolAuthService.verify(token);
        return commercialAreaService.analyze(request);
    }
}
