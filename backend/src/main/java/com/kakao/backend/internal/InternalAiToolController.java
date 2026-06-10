package com.kakao.backend.internal;

import com.kakao.backend.commercialarea.dto.CommercialAreaRequest;
import com.kakao.backend.commercialarea.dto.CommercialAreaResponse;
import com.kakao.backend.commercialarea.dto.RentEstimateResponse;
import com.kakao.backend.commercialarea.service.CommercialAreaService;
import com.kakao.backend.commercialarea.service.CommercialRentReferenceService;
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
    private final CommercialRentReferenceService rentReferenceService;

    public InternalAiToolController(
            InternalToolAuthService internalToolAuthService,
            SupportProgramService supportProgramService,
            CommercialAreaService commercialAreaService,
            CommercialRentReferenceService rentReferenceService
    ) {
        this.internalToolAuthService = internalToolAuthService;
        this.supportProgramService = supportProgramService;
        this.commercialAreaService = commercialAreaService;
        this.rentReferenceService = rentReferenceService;
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

    @PostMapping("/commercial-areas/rent-estimate")
    public RentEstimateResponse estimateCommercialRent(
            @RequestHeader(value = INTERNAL_TOKEN_HEADER, required = false) String token,
            @RequestBody Map<String, Object> request
    ) {
        internalToolAuthService.verify(token);
        return rentReferenceService.estimate(
                text(request.get("sido")),
                text(request.get("sigungu")),
                text(request.get("dong")),
                text(request.get("address")),
                number(request.get("areaM2")),
                text(request.get("commercialType"))
        );
    }

    private String text(Object value) {
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).trim();
        return text.isBlank() ? null : text;
    }

    private Double number(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value == null) {
            return null;
        }
        try {
            return Double.parseDouble(String.valueOf(value).replace(",", "").trim());
        } catch (NumberFormatException exception) {
            return null;
        }
    }
}
